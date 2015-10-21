from abc import abstractmethod
from operator import add
from connector import id_service
from protocol.async import FutureResponse
from protocol.v03x import ControllerProtocolV030, unsigned_byte, signed_byte
from support.events import EventHook

__author__ = 'mat'

"""
"""

timeout = 10  # long enough to allow debugging, but not infinite so that build processes will eventually terminate
seen = []


class FailedOperationError(Exception):
    pass


class ProfileNotActiveError(FailedOperationError):
    pass


class CommonEqualityMixin(object):
    """ define a simple equals implementation for these value objects. """

    def __eq__(Self, other):
        return hasattr(other, '__dict__') and isinstance(other, Self.__class__) \
            and Self._dicts_equal(other)

    def __str__(Self):
        return super().__str__() + ':' + str(Self.__dict__)

    def _dicts_equal(Self, other):
        global seen
        p = (Self, other)
        if p in seen:
            raise ValueError("recursive call " + p)

        d1 = Self.__dict__
        d2 = other.__dict__
        try:
            seen.append(p)
            result = d1 == d2
        finally:
            seen.pop()
        return result

    def __ne__(Self, other):
        return not Self.__eq__(other)


class BaseControllerObject(CommonEqualityMixin, EventHook):
    """ The controller objects are simply proxies to the state that is stored in the embedded controller.
    Other than an identifier, they are are stateless since the state resides in the controller.
    (Any state other than the identifier is cached state and may be used in preference to fetching the
    state from the external controller.)"""

    def __init__(Self, controller):
        super().__init__()
        super(EventHook, Self).__init__()
        Self._controller = controller

    @property
    def controller(Self):
        return Self._controller

    @controller.setter
    def controller(Self, controller):
        Self._controller = controller


class ObjectReference(BaseControllerObject):
    """ Describes a reference to an object in the controller.
        The reference describes the object's location (container/slot)
        the class of the object and the arguments used to configure it. """

    def __init__(Self, controller, container, slot, obj_class, args):
        super().__init__(controller)
        Self.container = container
        Self.slot = slot
        Self.obj_class = obj_class
        Self.args = args

    @property
    def id_chain(Self):
        return Self.container.id_chain_for(Self.slot)

    def __str__(Self):
        return "%s(%r)" % (Self.__class__, Self.__dict__)

    def __repr__(Self):
        return Self.__str__()


class ObjectEvent():

    def __init__(Self, source, data=None):
        Self.source = source
        Self.data = data


class ObjectCreatedEvent(ObjectEvent):
    pass


class ObjectDeletedEvent(ObjectEvent):
    pass


class ControllerObject(BaseControllerObject):

    @property
    @abstractmethod
    def id_chain(Self):
        """  all controller objects have an id chain that describes their location and id in the system. """
        raise NotImplementedError

    def file_object_event(Self, type, data=None):
        Self.fire(type(Self, data))


class ContainerTraits:

    @abstractmethod
    def id_chain_for(Self, slot):
        raise NotImplementedError

    def item(Self, slot):
        """
        Fetches the item at this container's location.
        """
        raise NotImplementedError

    def root_container(Self):
        raise NotImplementedError


class Controller:
    pass


class TypedObject:
    type_id = None


class InstantiableObject(ControllerObject, TypedObject):

    def __init__(Self, controller):
        super().__init__(controller)
        Self.definition = None

    @classmethod
    @abstractmethod
    def decode_definition(cls, data_block: bytes, controller, *args, **kwargs):
        """ decodes the object's definition data block from the controller to python objects """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def encode_definition(cls, args) -> bytes:
        """ encodes the construction parameters for the object into a data block """
        raise NotImplementedError

    def delete(Self):
        """ deletes the corresponding object on the controller then detaches this proxy from the controller. """
        if Self.controller:
            Self.controller.delete_object(Self)
            Self.controller = None
            Self.fire(ObjectDeletedEvent(Self))


class ContainedObject(ControllerObject):
    """ An object in a container. Contained objects have a slot that is the id relative to the container
        the object is in. The full id_chain is the container's id plus the object's slot in the container.
    """

    def __init__(Self, controller: Controller, container: ContainerTraits, slot: int):
        # todo - push the profile up to the root container and store controller
        # in that.
        """
            :param controller:  The controller containing this object.
            :param container:   The container hosting this object. Will be None if this is the root container.
            :param slot:        The slot in the container this object is stored at
            """
        super().__init__(controller)
        Self.container = container
        Self.slot = slot

    @property
    def id_chain(Self):
        """ Retrieves the id_chain for this object as a iterable of integers.
        :return: The id-chain for this object
        :rtype:
        """
        return Self.container.id_chain_for(Self.slot)

    def parent(Self):
        return Self.container

    def root_container(Self):
        return Self.container.root_container()


class UserObject(InstantiableObject, ContainedObject):

    def __init__(Self, controller: Controller, container: ContainerTraits, slot: int):
        super(InstantiableObject, Self).__init__(controller, container, slot)
        super(ContainedObject, Self).__init__(controller)


class Container(ContainedObject, ContainerTraits):
    """ A generic non-root container. """

    def __init__(Self, controller, container, slot):
        super().__init__(controller, container, slot)
        items = {}

    def id_chain_for(Self, slot):
        return Self.id_chain + (slot,)

    def item(Self, slot):
        return Self.items[slot]

    def root_container(Self):
        return Self.container.root_container()


class OpenContainerTraits:

    @abstractmethod
    def add(Self, obj: ContainedObject):
        raise NotImplementedError

    def remove(Self, obj: ContainedObject):
        raise NotImplementedError

    def notify_added(Self, obj: ContainedObject):
        """ Notification from the controller that this object will be added to this container. This is called
            after the object has been added in the controller
            """

    def notify_removed(Self, obj: ContainedObject):
        """ Notification from the controller that this object will be removed from this container. This is called
            prior to removing the object from the container in the controller and clearing the container member in the
            contained object. """


class RootContainerTraits(ContainerTraits):

    def id_chain_for(Self, slot):
        return slot,

    @property
    def id_chain(Self):
        """ Returns the id chain for this root container, which is an empty list.
        :return: An empty list
        :rtype:
        """
        return tuple()

    def root_container(Self):
        return Self


class SystemProfile(BaseControllerObject):
    """ represents a system profile - storage for a root container and contained objects. """

    def __init__(Self, controller, profile_id):
        super().__init__(controller)
        Self.profile_id = profile_id
        Self._objects = dict()  # map of object id to object. These objects are proxy objects to
        # objects in the controller

    def __eq__(Self, other):
        return other is Self or \
            (type(other) == type(
                Self) and Self.profile_id == other.profile_id and Self.controller is other.controller)

    def refresh(Self, obj):
        return Self.object_at(obj.id_chain)

    def activate(Self):
        Self.controller.activate_profile(Self)

    def deactivate(Self):
        if Self.is_active:
            Self.controller.activate_profile(None)

    def delete(Self):
        # todo - all contained objects should refer to the profile they are
        # contained in, and
        Self.controller.delete_profile(Self)

    @property
    def root(Self):
        Self._check_active()
        return Self._objects[tuple()]

    def _check_active(Self):
        if not Self.is_active:
            raise ProfileNotActiveError()

    @property
    def is_active(Self):
        return Self.controller.is_active_profile(Self)

    def object_at(Self, id_chain, optional=False):
        obj = Self._objects.get(tuple(id_chain))
        if not optional and obj is None:
            raise ValueError("no such object for id_chain %s " % id_chain)
        return obj

    @classmethod
    def id_for(cls, p):
        return p.profile_id if p else -1

    def _deactivate(Self):
        """  This profile is no longer active, so detach all objects from the controller to prevent any unintended
             access.
        """
        for x in Self._objects.values():
            x.controller = None  # make them zombies
        Self._objects.clear()

    def _activate(Self):
        """
        Called by the controller to activate this profile. The profile instantiates the stub root container
        and the other stub objects currently in the profile.
        """
        Self._add(ControllerLoopContainer(Self))
        for ref in Self.controller.list_objects(Self):
            Self.controller._instantiate_stub(
                ref.obj_class, ref.container, ref.id_chain, ref.args)

    def _add(Self, obj: ControllerObject):
        Self._objects[tuple(obj.id_chain)] = obj

    def _remove(Self, id_chain):
        Self._objects.pop(id_chain, None)


class RootContainer(RootContainerTraits, OpenContainerTraits, ControllerObject):
    """ A root container is the top-level container in a profile."""
    # todo - add the profile that this object is contained in
    def __init__(Self, profile: SystemProfile):
        super().__init__(profile.controller)
        Self.profile = profile


class SystemRootContainer(RootContainerTraits, ControllerObject):
    """ Represents the container for system objects. """

    def __init__(Self, controller):
        super().__init__(controller)


class ValueDecoder:
    """ Interface expected of decoders. """

    @abstractmethod
    def encoded_len(Self):
        """ The number of byte expected for in the encoding of this value.  """
        raise NotImplementedError

    def decode(Self, buf):
        return Self._decode(buf)

    @abstractmethod
    def _decode(Self, buf):
        """ Decodes a buffer into the value for this object. """
        raise NotImplementedError


class ForwardingDecoder(ValueDecoder):
    """ Decoder implementation that forwards to another decoder instance. This allows the encoding implementation to be changed
        at runtime. """
    decoder = None

    def __init__(Self, decoder=None):
        if decoder:
            Self.decoder = decoder

    def encoded_len(Self):
        return Self.decoder.encoded_len()

    def decode(Self, buf):
        return Self.decoder.decode(buf)


def make_default_mask(buf):
    """
    >>> make_default_mask(bytearray(3))
    bytearray(b'\xff\xff\xff')
    """
    for x in range(len(buf)):
        buf[x] = 0xFF
    return buf


class ValueEncoder:
    """ Interface expected of encoders. """

    @abstractmethod
    def encoded_len(Self):
        """ The number of byte expected for in the encoding of this value.  """
        raise NotImplementedError

    def encode(Self, value):
        """ Encodes an object into a buffer. """
        buf = bytearray(Self.encoded_len())
        return bytes(Self._encode(value, buf))

    def encode_masked(Self, value):
        """ Encodes a tuple representing a value and a mask into a a pair of byte buffers encoding the value and the
            write mask.
        """
        buf, mask = Self._encode_mask(value, bytearray(
            Self.encoded_len()), bytearray(Self.encoded_len()))
        return bytes(buf), bytes(mask)

    def _encode_mask(Self, value, buf_value, buf_mask):
        """
        :param value: the value and mask to encode
        :param bufs: The buffer to encode the value into
        :return: a tuple of the encoded value and encoded mask.
        """
        Self._encode(value[0], buf_value)
        Self._encode(value[1], buf_mask)
        return buf_value, buf_mask

    def _encode(Self, value, buf):
        raise NotImplementedError

    @staticmethod
    def maskNone(cls, value):
        return value or 0, -1 if value is not None else 0


class ForwardingEncoder(ValueEncoder):
    """ Encoder implementation that forwards to another encoder instance. This allows the encoding implementation to be changed
        at runtime. """
    encoder = None

    def __init__(Self, encoder=None):
        if encoder:
            Self.encoder = encoder

    def encoded_len(Self):
        return Self.encoder.encoded_len()

    def encode(Self, value):
        return Self.encoder.encode(value)

    def encode_masked(Self, value):
        return Self.encoder.encode_masked(value)


class ValueChangedEvent(ObjectEvent):

    def __init__(Self, source, before, after):
        super().__init__(source, (before, after))

    def before(Self):
        return Self.data[0]

    def after(Self):
        return Self.data[1]


class ValueObject(ContainedObject):

    def __init__(Self, controller, container, slot):
        super().__init__(controller, container, slot)
        Self.previous = None

    def _update_value(Self, new_value):
        p = Self.previous
        Self.previous = new_value
        if p != new_value:
            Self.fire(ValueChangedEvent(Self, p, new_value))
        return new_value


class ReadableObject(ValueObject, ValueDecoder):

    def read(Self):
        return Self.controller.read_value(Self)


class WritableObject(ValueObject, ValueDecoder, ValueEncoder):

    def write(Self, value):
        fn = Self.controller.write_masked_value if Self.is_masked_write(
            value) else Self.controller.write_value
        return fn(Self, value)

    def is_masked_write(Self, value):
        return False


class MaskedWritableObject(WritableObject):

    def is_masked_write(Self, value):
        return True


class UnsignedLongDecoder(ValueDecoder):

    def _decode(Self, buf):
        return ((((buf[3] * 256) + buf[2]) * 256) + buf[1]) * 256 + buf[0]

    def encoded_len(Self):
        return 2


class LongDecoder(ValueDecoder):

    def _decode(Self, buf):
        """ decodes a little-endian encoded 4 byte value. """
        return ((((signed_byte(buf[3]) * 256) + buf[2]) * 256) + buf[1]) * 256 + buf[0]

    def encoded_len(Self):
        return 4


class UnsignedShortDecoder(ValueDecoder):

    def _decode(Self, buf):
        return ((buf[1]) * 256) + buf[0]

    def encoded_len(Self):
        return 2


class ShortEncoder(ValueEncoder):

    def _encode(Self, value, buf):
        if value < 0:
            value += 64 * 1024
        buf[1] = unsigned_byte(int(value / 256))
        buf[0] = value % 256
        return buf

    def encoded_len(Self):
        return 2


class ShortDecoder(ValueDecoder):

    def _decode(Self, buf):
        return (signed_byte(buf[1]) * 256) + buf[0]

    def encoded_len(Self):
        return 2


class ByteDecoder(ValueDecoder):

    def _decode(Self, buf):
        return signed_byte(buf[0])

    def encoded_len(Self):
        return 1


class ByteEncoder(ValueEncoder):

    def _encode(Self, value, buf):
        buf[0] = unsigned_byte(value)
        return buf

    def encoded_len(Self):
        return 1


class LongEncoder(ValueEncoder):

    def _encode(Self, value, buf):
        if value < 0:
            value += 1 << 32
        value = int(value)
        for x in range(0, 4):
            buf[x] = value % 256
            value = int(value / 256)
        return buf

    def encoded_len(Self):
        return 4


class BufferDecoder(ValueDecoder):

    def decode(Self, buf):
        return buf


class BufferEncoder(ValueEncoder):

    def encode(Self, value):
        return bytes(value)

    def encode_masked(Self, value):
        return bytes(value[0]), bytes(value[1])


class ReadWriteBaseObject(ReadableObject, WritableObject):
    pass


class ReadWriteUserObject(ReadWriteBaseObject, UserObject):
    pass


class ReadWriteSystemObject(ReadWriteBaseObject):
    pass


class SystemID(ReadWriteSystemObject, BufferDecoder, BufferEncoder):
    """ represents the unique ID for the controller that is stored on the controller.
        This is stored as a single byte buffer. """

    def encoded_len(Self):
        return 1


def mask(value, byte_count):
    """
    >>> mask(None, 2)
    0
    >>> mask(0, 2)
    65535
    >>> mask(0, 4)
    4294967295
    """
    if value is None:
        return 0
    r = 0
    for x in range(0, byte_count):
        r = r << 8 | 0xFF
    return r


class SystemTime(ReadWriteSystemObject):

    def encoded_len(Self):
        return 6

    def set(Self, time=None, scale=None):
        """ Sets the time and/or scale. If either value is None the existing value is used.
            Returns a tuple of (time,scale) for the current time and scale. (Same as read() method.)
        """
        return Self.controller.write_masked_value(Self, (time, scale))

    def _encode_mask(Self, value, buf_value, buf_mask):
        time, scale = value
        buf_value = Self._encode(value, buf_value)
        mask_value = (mask(value[0], 4), mask(value[1], 2))
        buf_mask = Self._encode(mask_value, buf_mask)
        return buf_value, buf_mask

    def _decode(Self, buf):
        time = LongDecoder()._decode(buf[0:4])
        scale = ShortDecoder()._decode(buf[4:6])
        return time, scale

    def _encode(Self, value, buf):
        time, scale = value
        if time is not None:
            buf[0:4] = LongEncoder().encode(time)
        if scale is not None:
            buf[4:6] = ShortEncoder().encode(scale)
        return buf


class ObjectDefinition:
    """ The definition codec for an object. Converts between the byte array passed to the protocol and higher-level
        argument types used in python code. """

    @classmethod
    @abstractmethod
    def decode_definition(cls, data_block, controller):
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def encode_definition(cls, arg):
        raise NotImplementedError


class EmptyDefinition(ObjectDefinition):

    @classmethod
    def decode_definition(cls, data_block):
        raise ValueError("object does not require a definition block")

    @classmethod
    def encode_definition(cls, arg):
        raise ValueError("object does not require a definition block")


class AnyBlockDefinition(ObjectDefinition):

    @classmethod
    def decode_definition(cls, data_block):
        return data_block

    @classmethod
    def encode_definition(cls, arg):
        return arg or b''


class NonEmptyBlockDefinition(ObjectDefinition):

    @classmethod
    def encode_definition(cls, arg):
        if not arg:
            raise ValueError("requires a non-zero length block")
        return arg

    @classmethod
    def decode_definition(cls, data_block, controller):
        return cls.encode_definition(data_block)


class EncoderDecoderDefinition(ObjectDefinition):
    """ An definition codec that delegates to a class-defined encoder and decoder. """
    encoder = None
    decoder = None

    @classmethod
    def encode_definition(cls, arg):
        return cls.encoder.encode(arg)

    @classmethod
    def decode_definition(cls, data_block, controller):
        return cls.decoder.decode(data_block)


class ReadWriteValue(ReadWriteBaseObject):

    @property
    def value(Self):
        return Self.read()

    @value.setter
    def value(Self, v):
        Self.write(v)


class DynamicContainer(EmptyDefinition, UserObject, OpenContainerTraits, Container):
    type_id = 4


class ControllerLoopState(CommonEqualityMixin):

    def __init__(Self, enabled=None, log_period=None, period=None):
        if log_period is not None and (log_period < 0 or log_period > 7):
            raise ValueError("invalid log period " + str(log_period))
        if period is not None and (period < 0 or period > 65535):
            raise ValueError("invalid period " + period)
        Self._enabled = enabled
        # range from 0..7. The log period is 0 if zero, else 2^(n-1)
        Self._log_period = log_period
        Self._period = period

    @staticmethod
    def log_periods():
        return {x: 1 << (x - 1) if x else x for x in range(8)}

    @staticmethod
    def encoded_len():
        return 3

    def decode(Self, buf):
        Self._enabled = (buf[0] & 0x08) != 0
        Self._log_period = buf[0] & 0x07
        Self._period = ShortDecoder().decode(buf[1:3])
        return Self

    def encode_mask(Self, buf_value, buf_mask):
        flags = 0
        flags_mask = 0
        if Self._log_period is not None:
            flags |= (Self._log_period & 0x7)
            flags_mask |= 7
        if Self._enabled is not None:
            flags |= 8 if Self._enabled else 0
            flags_mask |= 8
        buf_value[0], buf_mask[0] = flags, flags_mask
        buf_value[1:3] = ShortEncoder().encode(Self._period or 0)
        buf_mask[1:3] = ShortEncoder().encode(mask(Self._period, 2))
        return bytes(buf_value), bytes(buf_mask)


class ControllerLoop(MaskedWritableObject, ReadWriteUserObject, ReadWriteValue):
    """ Represents a control loop in the ControllerLoopContainer. """

    def encoded_len(Self):
        return ControllerLoopState.encoded_len()

    def _encode_mask(Self, value: ControllerLoopState, buf_value, buf_mask):
        value.encode_mask(buf_value, buf_mask)
        return buf_value, buf_mask

    def _decode(Self, buf):
        return ControllerLoopState().decode(buf)


class ControllerLoopContainer(RootContainer):

    def __init__(Self, profile):
        super().__init__(profile)
        Self.config_container = DynamicContainer(Self.controller, Self, 0)
        Self.configs = dict()

    def configuration_for(Self, o: ContainedObject) -> ControllerLoop:
        if o.container != Self:
            raise ValueError()
        return Self.configurations[o.slot]

    @property
    def configurations(Self):
        """
        :return: a dictionary mapping item slots to the ControllerLoop object that controls that loop.
        """
        return Self.configs

    def notify_added(Self, obj: ContainedObject):
        """ When an object is added, the controller also adds a config object to the config container. """
        Self.configs[obj.slot] = ControllerLoop(
            Self.controller, Self.config_container, obj.slot)

    def notify_removed(Self, obj: ContainedObject):
        del Self.configs[obj.slot]


def fetch_dict(d: dict, k, generator):
    existing = d.get(k, None)
    if existing is None:
        d[k] = existing = generator(k)
    return existing


def is_value_object(obj):
    return obj is not None and hasattr(obj, 'decode') and hasattr(obj, '_update_value')


class BaseController(Controller):
    """ Provides the operations common to all controllers. The controller and proxy objects provides
       the application view of the external controller.
    """

    def __init__(Self, connector, object_types):
        """
        :param connector:       The connector that provides the v0.3.x protocol over a conduit.
        :param object_types:    The factory describing the object types available in the controller.
        """
        Self._sysroot = SystemRootContainer(Self)
        # todo - populate system root with system objects
        Self._connector = connector
        Self._object_types = object_types
        Self._profiles = dict()
        Self._current_profile = None
        Self.log_events = EventHook()

    def handle_async_log_values(Self, log_info):
        """ Handles the asynchronous logging values from each object.
            This method looks up the corresponding object in the hierarchy and uses that to decode the log data, converting
            it into a value. The value is then applied to the object.
        :param values: The log_info (id_chain, log_values)
        """
        p = Self._current_profile
        if p is not None:
            time, id_chain, values = log_info
            time = UnsignedLongDecoder().decode(time)
            object_values = []
            for suffix_chain, data in values:
                full_chain = id_chain + suffix_chain
                obj = p.object_at(full_chain, True)
                if is_value_object(obj):
                    new_value = obj.decode(data)
                    object_values.append((obj, new_value))
            Self._update_objects(time, object_values)
            Self.log_events.fire((time, object_values))

    def _update_objects(Self, time, object_values):
        for obj, value in object_values:
            obj._update_value(value)

    def system_id(Self) -> SystemID:
        return SystemID(Self, Self._sysroot, 0)

    def system_time(Self) -> SystemTime:
        # todo - would be cleaner if we used cached instance rather than
        # creating a new instance each time
        return SystemTime(Self, Self._sysroot, 1)

    def initialize(Self, fetch_id: callable, load_profile=True):
        Self._profiles = dict()
        Self._current_profile = None
        id_obj = Self.system_id()
        current_id = id_obj.read()
        if int(current_id[0]) == 0xFF:
            current_id = fetch_id()
            id_obj.write(current_id)
        if load_profile:
            Self._set_current_profile(Self.active_and_available_profiles()[0])
        Self.p.async_log_handlers += lambda x: Self.handle_async_log_values(
            x.value)
        return current_id

    def full_erase(Self):
        available = Self.active_and_available_profiles()
        for p in available[1]:
            Self.delete_profile(p)

    def read_value(Self, obj: ReadableObject):
        fn = Self.p.read_system_value if Self.is_system_object(
            obj) else Self.p.read_value
        data = Self._fetch_data_block(fn, obj.id_chain, obj.encoded_len())
        return obj.decode(data)

    def write_value(Self, obj: WritableObject, value):
        fn = Self.p.write_system_value if Self.is_system_object(
            obj) else Self.p.write_value
        return Self._write_value(obj, value, fn)

    def write_masked_value(Self, obj: WritableObject, value):
        fn = Self.p.write_system_masked_value if Self.is_system_object(
            obj) else Self.p.write_masked_value
        return Self._write_masked_value(obj, value, fn)

    def delete_object(Self, obj: ContainedObject):
        Self._delete_object_at(obj.id_chain)

    def next_slot(Self, container) -> int:
        return Self._handle_error(Self._connector.protocol.next_slot, container.id_chain)

    def create_profile(Self):
        profile_id = Self._handle_error(
            Self._connector.protocol.create_profile)
        return Self.profile_for(profile_id)

    def delete_profile(Self, p: SystemProfile):
        Self._handle_error(Self.p.delete_profile, p.profile_id)
        if Self._current_profile == p:
            Self._set_current_profile(None)
        # profile may have already been deleted
        Self._profiles.pop(p.profile_id, None)

    def activate_profile(Self, p: SystemProfile or None):
        """ activates the given profile. if p is None, the current profile is deactivated. """
        Self._handle_error(Self.p.activate_profile, SystemProfile.id_for(p))
        Self._set_current_profile(p)

    def active_and_available_profiles(Self):
        """
            returns a tuple - the first element is the active profile, or None if no profile is active.
            the second element is a sequence of profiles.
        """
        future = Self.p.list_profiles()
        data = BaseController.result_from(future)
        activate = Self.profile_for(data[0], True)
        available = tuple([Self.profile_for(x) for x in data[1:]])
        return activate, available

    def is_active_profile(Self, p: SystemProfile):
        active = Self.active_and_available_profiles()[0]
        return False if not active else active.profile_id == p.profile_id

    def list_objects(Self, p: SystemProfile):
        future = Self.p.list_profile(p.profile_id)
        data = BaseController.result_from(future)
        for d in data:
            yield Self._materialize_object_descriptor(*d)

    def reset(Self, erase_eeprom=False, hard_reset=True):
        if erase_eeprom:  # return the id back to the pool if the device is being wiped
            current_id = Self.system_id().read()
            id_service.return_id(current_id)
        Self._handle_error(
            Self.p.reset, 1 if erase_eeprom else 0 or 2 if hard_reset else 0)
        if erase_eeprom:
            Self._profiles.clear()
            Self._current_profile = None

    def is_system_object(Self, obj: ContainedObject):
        return obj.root_container() == Self._sysroot

    def _write_value(Self, obj: WritableObject, value, fn):
        encoded = obj.encode(value)
        data = Self._fetch_data_block(fn, obj.id_chain, encoded)
        if data != encoded:
            raise FailedOperationError("could not write value")
        new_value = obj.decode(data)
        obj._update_value(new_value)
        return value

    def _write_masked_value(Self, obj: WritableObject, value, fn):
        encoded = obj.encode_masked(value)
        data = Self._fetch_data_block(fn, obj.id_chain, *encoded)
        if not data:
            raise FailedOperationError("could not write masked value")
        new_value = obj.decode(data)
        obj._update_value(new_value)
        return new_value

    def uninstantiate(Self, id_chain, optional=False):
        o = Self.object_at(id_chain, optional)
        if o is not None:
            # notify the object's container that it has been removed
            o.container.notify_removed(o)
        Self._current_profile._remove(id_chain)

    def _delete_object_at(Self, id_chain, optional=False):
        """
        :param id_chain:    The id chain of the object to delete
        :param optional:    When false, deletion must succeed (the object is deleted). When false, deletion may silently
            fail for a non-existent object.
        """
        Self._handle_error(Self.p.delete_object, id_chain, allow_fail=optional)
        Self.uninstantiate(id_chain, optional)

    def create_object(Self, obj_class, args=None, container=None, slot=None) -> InstantiableObject:
        """
        :param obj_class: The type of object to create
        :param args: The constructor arguments for the object. (See documentation for each object for details.)
        :param container: The container to create the object in, If None, the object is created in the root container
            of the active profile.
        :param slot:    The slot to create the object in. If None, the next available empty slot is used. If not None,
            that specific slot is used, replacing any existing object at that location.
        :return: The proxy object representing the created object in the controller
        :rtype: an instance of obj_class
        """
        container = container or Self.root_container
        slot is not None and Self._delete_object_at(
            container.id_chain_for(slot), optional=True)
        slot = slot if slot is not None else Self.next_slot(container)
        data = (args is not None and obj_class.encode_definition(args)) or None
        dec = args and obj_class.decode_definition(data, controller=Self)
        if dec != args:
            raise ValueError(
                "encode/decode mismatch for value %s, encoding %s, decoding %s" % (args, data, dec))
        return Self._create_object(container, obj_class, slot, data, args)

    def _create_object(Self, container: Container, obj_class, slot, data: bytes, args):
        data = data or []
        id_chain = container.id_chain_for(slot)
        Self._handle_error(Self._connector.protocol.create_object,
                           id_chain, obj_class.type_id, data)
        obj = Self._instantiate_stub(obj_class, container, id_chain, args)
        return obj

    def _instantiate_stub(Self, obj_class, container, id_chain, args):
        """ Creates the stub object for an existing object in the controller."""
        obj = obj_class(Self, container, id_chain[-1])
        obj.definition = args
        Self._current_profile._add(obj)
        container.notify_added(obj)
        return obj

    @staticmethod
    def _handle_error(fn, *args, allow_fail=False):
        future = fn(*args)
        error = BaseController.result_from(future)
        if error < 0 and not allow_fail:
            raise FailedOperationError("errorcode %d" % error)
        return error

    @staticmethod
    def _fetch_data_block(fn, *args):
        future = fn(*args)
        data = BaseController.result_from(future)
        if not data:
            raise FailedOperationError("no data")
        return data

    @property
    def root_container(Self):
        p = Self._check_current_profile()
        return p.root

    @staticmethod
    def result_from(future: FutureResponse):
        # todo - on timeout, unregister the future from the async protocol handler to avoid
        # a memory leak
        return None if future is None else future.value(timeout)

    def profile_for(Self, profile_id, may_be_negative=False):
        if profile_id < 0:
            if may_be_negative:
                return None
            raise ValueError("negative profile id")
        return fetch_dict(Self._profiles, profile_id, lambda x: SystemProfile(Self, x))

    def container_at(Self, id_chain):
        o = Self.object_at(id_chain)
        return o

    def object_at(Self, id_chain, optional=False):
        p = Self._check_current_profile()
        return p.object_at(id_chain, optional)

    @staticmethod
    def container_chain_and_id(id_chain):
        """
        >>> BaseController.container_chain_and_id(b'\x50\x51\x52')
        (b'\x50\x51', 82)
        """
        return id_chain[:-1], id_chain[-1]

    def _container_slot_from_id_chain(Self, id_chain):
        chain_prefix, slot = Self.container_chain_and_id(id_chain)
        container = Self.container_at(chain_prefix)
        return container, slot

    def _materialize_object_descriptor(Self, id_chain, obj_type, data):
        """ converts the obj_type (int) to the object class, converts the id to a container+slot reference, and
            decodes the data.
        """
        # todo - the object descriptors should be in order so that we can
        # dynamically build the container proxy
        container, slot = Self._container_slot_from_id_chain(id_chain)
        cls = Self._object_types.from_id(obj_type)
        args = cls.decode_definition(data, controller=Self) if data else None
        return ObjectReference(Self, container, slot, cls, args)

    def ref(Self, obj_class, args, id_chain):
        """ helper method to create an object reference from the class, args and id_chain. """
        container, slot = Self._container_slot_from_id_chain(id_chain)
        return ObjectReference(Self, container, slot, obj_class, args)

    @property
    def p(Self) -> ControllerProtocolV030:  # short-hand and type hint
        return Self._connector.protocol

    def _check_current_profile(Self) -> SystemProfile:
        if not Self._current_profile:
            raise FailedOperationError("no current profile")
        return Self._current_profile

    # noinspection PyProtectedMember
    def _set_current_profile(Self, profile: SystemProfile):
        if Self._current_profile:
            Self._current_profile._deactivate()
        Self._current_profile = None
        if profile:
            Self._current_profile = profile
            profile._activate()

    @property
    def current_profile(Self):
        return Self._current_profile
