from abc import abstractmethod
from connector import id_service
from protocol.async import FutureResponse
from protocol.v03x import ControllerProtocolV030, unsigned_byte, signed_byte
from support.events import EventHook

__author__ = 'mat'

"""
"""

timeout = 10  # long enough to allow debugging, but not infinite so that build processes will eventually terminate
seen = False

class FailedOperationError(Exception):
    pass

class ProfileNotActiveError(FailedOperationError):
    pass

class CommonEqualityMixin(object):
    """ define a simple equals implementation for these value objects. """

    def __eq__(self, other):
        return hasattr(other, '__dict__') and isinstance(other, self.__class__) \
            and self._dicts_equal(other)

    def __str__(self):
        return super().__str__()+':'+str(self.__dict__)


    def _dicts_equal(self, other):
        global seen
        if seen:
            raise ValueError("recursive call")

        d1 = self.__dict__
        d2 = other.__dict__
        try:
            seen = True
            result = d1==d2
        finally:
            seen = False
        return result

    def __ne__(self, other):
        return not self.__eq__(other)


class BaseControllerObject(CommonEqualityMixin, EventHook):
    """ The controller objects are simply proxies to the state that is stored in the embedded controller.
    Other than an identifier, they are are stateless since the state resides in the controller.
    (Any state other than the identifier is cached state and may be used in preference to fetching the
    state from the external controller.)"""

    def __init__(self, controller):
        super().__init__()
        super(EventHook, self).__init__()
        self._controller = controller

    @property
    def controller(self):
        return self._controller

    @controller.setter
    def controller(self, controller):
        self._controller = controller


class ObjectReference(BaseControllerObject):
    """ Describes a reference to an object in the controller.
        The reference describes the object's location (container/slot)
        the class of the object and the arguments used to configure it. """

    def __init__(self, controller, container, slot, obj_class, args):
        super().__init__(controller)
        self.container = container
        self.slot = slot
        self.obj_class = obj_class
        self.args = args

    @property
    def id_chain(self):
        return self.container.id_chain_for(self.slot)

    def __str__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)

    def __repr__(self):
        return self.__str__()


class ObjectEvent():
    def __init__(self, source, data=None):
        self.source = source
        self.data = data

class ObjectCreatedEvent(ObjectEvent):
    pass

class ObjectDeletedEvent(ObjectEvent):
    pass


class ControllerObject(BaseControllerObject):
    @property
    @abstractmethod
    def id_chain(self):
        """  all controller objects have an id chain that describes their location and id in the system. """
        raise NotImplementedError

    def file_object_event(self, type, data=None):
        self.fire(type(self, data))


class ContainerTraits:
    @abstractmethod
    def id_chain_for(self, slot):
        raise NotImplementedError

    def item(self, slot):
        """
        Fetches the item at this container's location.
        """
        raise NotImplementedError


class Controller:
    pass


class TypedObject:
    type_id = None


class InstantiableObject(ControllerObject, TypedObject):
    def __init__(self, controller):
        super().__init__(controller)
        self.definition = None

    @classmethod
    @abstractmethod
    def decode_definition(cls, data_block: bytes, controller):
        """ decodes the object's definition data block from the controller to python objects """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def encode_definition(cls, args) -> bytes:
        """ encodes the construction parameters for the object into a data block """
        raise NotImplementedError

    def delete(self):
        """ deletes the corresponding object on the controller then detaches this proxy from the controller. """
        if self.controller:
            self.controller.delete_object(self)
            self.controller = None
            self.fire(ObjectDeletedEvent(self))


class ContainedObject(ControllerObject):
    """ An object in a container. Contained objects have a slot that is the id relative to the container
        the object is in. The full id_chain is the container's id plus the object's slot in the container.
    """
    def __init__(self, controller: Controller, container: ContainerTraits, slot: int):
        # todo - push the profile up to the root container and store controller in that.
        """
            :param controller:  The controller containing this object.
            :param container:   The container hosting this object. Will be None if this is the root container.
            :param slot:        The slot in the container this object is stored at
            """
        super().__init__(controller)
        self.container = container
        self.slot = slot

    @property
    def id_chain(self):
        """ Retrieves the id_chain for this object as a iterable of integers.
        :return: The id-chain for this object
        :rtype:
        """
        return self.container.id_chain_for(self.slot)


class UserObject(InstantiableObject, ContainedObject):
    def __init__(self, controller: Controller, container: ContainerTraits, slot: int):
        super(InstantiableObject, self).__init__(controller, container, slot)
        super(ContainedObject, self).__init__(controller)


class Container(ContainedObject, ContainerTraits):
    def __init__(self, controller, container, slot):
        super().__init__(controller, container, slot)
        items = {}

    def id_chain_for(self, slot):
        return self.id_chain + (slot,)

    def item(self, slot):
        return self.items[slot]


class OpenContainerTraits:
    @abstractmethod
    def add(self, obj:ContainedObject):
        raise NotImplementedError

    def remove(self, obj:ContainedObject):
        raise NotImplementedError


class RootContainerTraits(ContainerTraits):
    def id_chain_for(self, slot):
        return slot,

    @property
    def id_chain(self):
        """ Returns the id chain for this root container, which is an empty list.
        :return: An empty list
        :rtype:
        """
        return tuple()


class RootContainer(RootContainerTraits, OpenContainerTraits, ControllerObject):
    """ A root container is the top-level container in a profile."""
    # todo - add the profile that this object is contained in
    def __init__(self, profile):
        super().__init__(profile.controller)
        self.profile = profile


class SystemRootContainer(RootContainerTraits, ControllerObject):
    def __init__(self, controller):
        super().__init__(controller)


class SystemProfile(BaseControllerObject):
    """ represents a system profile - storage for a root container and contained objects. """
    def __init__(self, controller, profile_id):
        super().__init__(controller)
        self.profile_id = profile_id
        self._objects = dict()  # map of object id to object. These objects are proxy objects to
                                # objects in the controller

    def activate(self):
        self.controller.activate_profile(self)

    def deactivate(self):
        if self.is_active:
            self.controller.activate_profile(None)

    def delete(self):
        # todo - all contained objects should refer to the profile they are contained in, and
        self.controller.delete_profile(self)

    @property
    def root(self):
        self._check_active()
        return self._objects[tuple()]

    def _check_active(self):
        if not self.is_active:
            raise ProfileNotActiveError()

    @property
    def is_active(self):
        return self.controller.is_active_profile(self)

    def object_at(self, id_chain):
        obj = self._objects.get(tuple(id_chain))
        if obj is None:
            raise ValueError("no such object for id_chain %s " % id_chain)
        return obj

    @classmethod
    def id_for(cls, p):
        return p.profile_id if p else -1

    def _deactivate(self):
        """  This profile is no longer active, so detach all objects from the controller to prevent any unintended
             access.
        """
        for x in self._objects.values():
            x.controller = None # make them zombies
        self._objects.clear()

    def _activate(self):
        """
        Called by the controller to activate this profile. The profile instantiates the stub root container
        and the other stub objects currently in the profile.
        """
        self._add([], RootContainer(self))
        for ref in self.controller.list_objects(self):
            self.controller._instantiate_stub(ref.obj_class, ref.container, ref.id_chain, ref.args)

    def _add(self, id_chain, obj):
        self._objects[tuple(id_chain)] = obj

    def _remove(self, id_chain):
        self._objects.pop(id_chain, None)


class ValueDecoder:
    @abstractmethod
    def encoded_len(self):
        """ The number of byte expected for in the encoding of this value.  """
        raise NotImplementedError

    def decode(self, buf):
        return self._decode(buf)

    @abstractmethod
    def _decode(self, buf):
        """ Decodes a buffer into the value for this object. """
        raise NotImplementedError


class ValueEncoder:
    @abstractmethod
    def encoded_len(self):
        """ The number of byte expected for in the encoding of this value.  """
        raise NotImplementedError

    def encode(self, value):
        """ Encodes an object into a buffer. """
        buf = bytearray(self.encoded_len())
        return bytes(self._encode(value, buf))

    @abstractmethod
    def _encode(self, value, buf):
        raise NotImplementedError

class ValueChangedEvent(ObjectEvent):
    def __init__(self, source, before, after):
        super().__init__(source, (before, after))

    def before(self):
        return self.data[0]

    def after(self):
        return self.data[1]


class ValueObject(ContainedObject):
    def __init__(self, controller, container, slot):
        super().__init__(controller, container, slot)
        self.previous = None

    def update(self, new_value):
        p = self.previous
        self.previous = new_value
        if p!=new_value:
            self.fire(ValueChangedEvent(self, p, new_value))
        return new_value


class ReadableObject(ValueObject, ValueDecoder):
    def read(self):
        return self.update(self.controller.read_value(self))



class WritableObject(ValueObject, ValueDecoder, ValueEncoder):
    def write(self, value):
        self.controller.write_value(self, value)
        self.update(value)


class LongDecoder(ValueDecoder):
    def _decode(self, buf):
        """ decodes a little-endian encoded 4 byte value. """
        return ((((signed_byte(buf[3]) * 256) + buf[2]) * 256) + buf[1]) * 256 + buf[0]

    def encoded_len(self):
        return 4

class UnsignedShortDecoder(ValueDecoder):
    def _decode(self, buf):
        return ((buf[1]) * 256) + buf[0]

    def encoded_len(self):
        return 2


class ShortEncoder(ValueEncoder):
    def _encode(self, value, buf):
        if value < 0:
            value += 64 * 1024
        buf[1] = unsigned_byte(int(value / 256))
        buf[0] = value % 256
        return buf

    def encoded_len(self):
        return 2


class ShortDecoder(ValueDecoder):
    def _decode(self, buf):
        return (signed_byte(buf[1]) * 256) + buf[0]

    def encoded_len(self):
        return 2


class ByteDecoder(ValueDecoder):
    def _decode(self, buf):
        return signed_byte(buf[0])

    def encoded_len(self):
        return 1


class ByteEncoder(ValueEncoder):
    def _encode(self, value, buf):
        buf[0] = unsigned_byte(value)
        return buf

    def encoded_len(self):
        return 1

class LongEncoder(ValueEncoder):
    def _encode(self, value, buf):
        if value < 0:
            value += 1 << 32
        value = int(value)
        for x in range(0, 4):
            buf[x] = value % 256
            value = int(value / 256)
        return buf

    def encoded_len(self):
        return 4


class BufferDecoder(ValueDecoder):
    def decode(self, buf):
        return buf


class BufferEncoder(ValueEncoder):
    def encode(self, value):
        return value


class ReadWriteBaseObject(ReadableObject, WritableObject):
    pass


class ReadWriteUserObject(ReadWriteBaseObject, UserObject):
    pass


class ReadWriteSystemObject(ReadWriteBaseObject):
    def read(self):
        return self.controller.read_system_value(self)

    def write(self, value):
        self.controller.write_system_value(self, value)


class SystemID(ReadWriteSystemObject, BufferDecoder, BufferEncoder):
    """ represents the unique ID for the controller that is stored on the controller.
        This is stored as a single byte buffer. """

    def encoded_len(self):
        return 1


class SystemTime(ReadWriteSystemObject):
    def encoded_len(self):
        return 6

    def _decode(self, buf):
        time = LongDecoder()._decode(buf[0:4])
        scale = ShortDecoder()._decode(buf[4:6])
        return time, scale

    def _encode(self, value, buf):
        time, scale = value
        buf[0:4] = LongEncoder().encode(time)
        buf[4:6] = ShortEncoder().encode(scale)
        return buf


class ObjectDefinition:
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


class ReadWriteValue(ReadWriteBaseObject):
    @property
    def value(self):
        return self.read()

    @value.setter
    def value(self, v):
        self.write(v)


def fetch_dict(d:dict, k, generator):
    existing = d.get(k, None)
    if existing is None:
        d[k] = existing = generator(k)
    return existing


class BaseController(Controller):
    """ provides the operations common to all controllers.
    """

    def __init__(self, connector, object_types):
        """
        :param connector:       The connector that provides the v0.3.x protocol over a conduit.
        :param object_types:    The factory describing the object types available in the controller.
        """
        self._sysroot = SystemRootContainer(self)
        self.connector = connector
        self.object_types = object_types
        self.profiles = dict()
        self.current_profile = None

    def system_id(self) -> SystemID:
        return SystemID(self, self._sysroot, 0)

    def system_time(self) -> SystemTime:
        return SystemTime(self, self._sysroot, 1)

    def initialize(self, fetch_id:callable):
        self.profiles = dict()
        self.current_profile = None
        id_obj = self.system_id()
        current_id = id_obj.read()
        if int(current_id[0]) == 0xFF:
            current_id = fetch_id()
            id_obj.write(current_id)
        self._set_current_profile(self.active_and_available_profiles()[0])
        return current_id

    def full_erase(self):
        available = self.active_and_available_profiles()
        for p in available[1]:
            self.delete_profile(p)

    def read_value(self, obj: ReadableObject):
        data = self._fetch_data_block(self.p.read_value, obj.id_chain, obj.encoded_len())
        return obj.decode(data)

    def write_value(self, obj: WritableObject, value):
        self._write_value(obj, value, self.p.write_value)

    def delete_object(self, obj: ContainedObject):
        self._delete_object_at(obj.id_chain)

    def next_slot(self, container) -> int:
        return self._handle_error(self.connector.protocol.next_slot, container.id_chain)

    def create_profile(self):
        profile_id = self._handle_error(self.connector.protocol.create_profile)
        return self.profile_for(profile_id)

    def delete_profile(self, p: SystemProfile):
        self._handle_error(self.p.delete_profile, p.profile_id)
        if self.current_profile == p:
            self._set_current_profile(None)
        self.profiles.pop(p.profile_id, None)   # profile may have already been deleted

    def activate_profile(self, p: SystemProfile or None):
        """ activates the given profile. if p is None, the current profile is deactivated. """
        self._handle_error(self.p.activate_profile, SystemProfile.id_for(p))
        self._set_current_profile(p)

    def active_and_available_profiles(self):
        """
            returns a tuple - the first element is the active profile, or None if no profile is active.
            the second element is a sequence of profiles.
        """
        future = self.p.list_profiles()
        data = BaseController.result_from(future)
        activate = self.profile_for(data[0], True)
        available = tuple([self.profile_for(x) for x in data[1:]])
        return activate, available

    def is_active_profile(self, p: SystemProfile):
        active = self.active_and_available_profiles()[0]
        return False if not active else active.profile_id == p.profile_id

    def list_objects(self, p: SystemProfile):
        future = self.p.list_profile(p.profile_id)
        data = BaseController.result_from(future)
        for d in data:
            yield self._materialize_object_descriptor(*d)

    def reset(self, erase_eeprom=False, hard_reset=True):
        if erase_eeprom:  # return the id back to the pool if the device is being wiped
            current_id = self.system_id().read()
            id_service.return_id(current_id)
        self._handle_error(self.p.reset, 1 if erase_eeprom else 0 or 2 if hard_reset else 0)
        if erase_eeprom:
            self.profiles.clear()
            self.current_profile = None

    def read_system_value(self, obj: ReadableObject):
        data = self._fetch_data_block(self.p.read_system_value, obj.id_chain, obj.encoded_len())
        return obj.decode(data)

    def write_system_value(self, obj: WritableObject, value):
        self._write_value(obj, value, self.p.write_system_value)

    def _write_value(self, obj: WritableObject, value, fn):
        encoded = obj.encode(value)
        data = self._fetch_data_block(fn, obj.id_chain, encoded)
        if data != encoded:
            raise FailedOperationError("could not write value")

    def _delete_object_at(self, id_chain, optional=False):
        """
        :param id_chain:    The id chain of the object to delete
        :param optional:    When false, deletion must succeed (the object is deleted). When false, deletion may silently
            fail for a non-existent object.
        """
        self._handle_error(self.p.delete_object, id_chain, allow_fail=optional)
        self.current_profile._remove(id_chain)

    def create_object(self, obj_class, args=None, container=None, slot=None) -> InstantiableObject:
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
        container = container or self.root_container
        slot is not None and self._delete_object_at(container.id_chain_for(slot), optional=True)
        slot = slot if slot is not None else self.next_slot(container)
        data = (args is not None and obj_class.encode_definition(args)) or None
        dec = args and obj_class.decode_definition(data, controller=self)
        if dec != args:
            raise ValueError("encode/decode mismatch for value %s, encoding %s, decoding %s" % (args, data, dec))
        return self._create_object(container, obj_class, slot, data, args)

    def _create_object(self, container: Container, obj_class, slot, data: bytes, args):
        data = data or []
        id_chain = container.id_chain_for(slot)
        self._handle_error(self.connector.protocol.create_object, id_chain, obj_class.type_id, data)
        obj = self._instantiate_stub(obj_class, container, id_chain, args)
        return obj

    def _instantiate_stub(self, obj_class, container, id_chain, args):
        """ Creates the stub object for an existing object in the controller."""
        obj = obj_class(self, container, id_chain[-1])
        obj.definition = args
        self.current_profile._add(id_chain, obj)
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
    def root_container(self):
        p = self._check_current_profile()
        return p.root

    @staticmethod
    def result_from(future: FutureResponse):
        # todo - on timeout, unregister the future from the async protocol handler to avoid
        # a memory leak
        return None if future is None else future.value(timeout)

    def profile_for(self, profile_id, may_be_negative=False):
        if profile_id < 0:
            if may_be_negative:
                return None
            raise ValueError("negative profile id")
        return fetch_dict(self.profiles, profile_id, lambda x: SystemProfile(self, x))

    def container_at(self, id_chain):
        o = self.object_at(id_chain)
        return o

    def object_at(self, id_chain):
        p = self._check_current_profile()
        return p.object_at(id_chain)

    @staticmethod
    def container_chain_and_id(id_chain):
        """
        >>> BaseController.container_chain_and_id(b'\x50\x51\x52')
        (b'\x50\x51', 82)
        """
        return id_chain[:-1], id_chain[-1]

    def _container_slot_from_id_chain(self, id_chain):
        chain_prefix, slot = self.container_chain_and_id(id_chain)
        container = self.container_at(chain_prefix)
        return container, slot

    def _materialize_object_descriptor(self, id_chain, obj_type, data):
        """ converts the obj_type (int) to the object class, converts the id to a container+slot reference, and
            decodes the data.
        """
        # todo - the object descriptors should be in order so that we can dynamically build the container proxy
        container, slot = self._container_slot_from_id_chain(id_chain)
        cls = self.object_types.from_id(obj_type)
        args = cls.decode_definition(data, controller=self) if data else None
        return ObjectReference(self, container, slot, cls, args)

    def ref(self, obj_class, args, id_chain):
        """ helper method to create an object reference from the class, args and id_chain. """
        container, slot = self._container_slot_from_id_chain(id_chain)
        return ObjectReference(self, container, slot, obj_class, args)

    @property
    def p(self) -> ControllerProtocolV030:  # short-hand and type hint
        return self.connector.protocol

    def _check_current_profile(self)->SystemProfile:
        if not self.current_profile:
            raise FailedOperationError("no current profile")
        return self.current_profile

    # noinspection PyProtectedMember
    def _set_current_profile(self, profile: SystemProfile):
        if self.current_profile:
            self.current_profile._deactivate()
        self.current_profile = None
        if profile:
            self.current_profile = profile
            profile._activate()


