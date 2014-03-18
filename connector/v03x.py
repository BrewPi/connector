from abc import abstractmethod, ABCMeta
from connector import controller_id
from protocol.async import FutureResponse

__author__ = 'mat'

"""
"""

timeout = 3000  # long enough to allow debugging, but not infinite so that build processes will eventually terminate


class FailedOperationError(Exception):
    pass


""" The controller objects are simply proxies to the state that is stored in the embedded controller.
    Other than an identifier, they are are stateless since the state resides in the controller.
    (Any state other than the identifier is cached state and may be used in preference to fetching the
    state from the external controller.)"""


class CommonEqualityMixin(object):
    """ define a simple equals implementation for these value objects. """
    def __eq__(self, other):
        return hasattr(other, '__dict__') and isinstance(other, self.__class__) \
            and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self.__eq__(other)


class BaseControllerObject(CommonEqualityMixin):
    def __init__(self, controller):
        self.controller = controller


class ControllerObject(BaseControllerObject, metaclass=ABCMeta):
    @property
    @abstractmethod
    def id_chain(self):
        """  all controller objects have an id chain that describes their location and id in the system. """
        raise NotImplementedError


class ContainerTraits:
    pass


class BaseController:
    pass


class ContainedObject(ControllerObject):
    """ An object in a container. Contained objects have a slot that is the id relative to the container
        the object is in. The full id_chain is the container's id plus the object's slot in the container.
    """

    def __init__(self, controller: BaseController, container: ContainerTraits, slot: int):
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
        """ Retrieves the id_chain for this object as a interable of integers.
        :return: The id-chain for this object
        :rtype:
        """
        return self.container.id_chain_for(self.slot)

    def delete(self):
        """ deletes the corresponding object on the controller then detaches this proxy from the controller. """
        if self.controller:
            self.controller.delete_object(self)
            self.container = None
            self.slot = None
            self.controller = None

class ContainerTraits:
    @abstractmethod
    def id_chain_for(self, slot):
        raise NotImplementedError


class Container(ContainedObject, ContainerTraits):
    def id_chain_for(self, slot):
        return self.container.id_chain + (slot,)


class RootContainer(ControllerObject, ContainerTraits):
    """ A root container is the top-level container - it is not contained in any container. """
    # todo - add the profile that this object is contained in

    def __init__(self, controller: BaseController):
        super().__init__(controller)

    def id_chain_for(self, slot):
        return slot,

    @property
    def id_chain(self):
        """ Returns the id chain for this root container, which is an empty list.
        :return: An empty list
        :rtype:
        """
        return tuple()

class Profile:
    pass


class Profile(BaseControllerObject):
    """ represents a profile. """

    def __init__(self, controller, profile_id):
        super().__init__(controller)
        self.profile_id = profile_id

    def activate(self):
        self.controller.activate_profile(self)

    def deactivate(self):
        if self.is_active:
            self.controller.activate_profile(self)

    def delete(self):
        # todo - all contained objects should refer to the profile they are contained in, and
        self.controller.delete_profile(self)

    @property
    def is_active(self):
        return self.controller.is_active_profile(self)

    @classmethod
    def id_for(cls, p:Profile):
        return p.profile_id if p else -1



class ObjectType:
    """ the type ids for all objects that are instantiable in the controller. """
    current_ticks = 3


class ValueDecoder:
    @abstractmethod
    def encoded_len(self):
        """ The number of byte expected for in the encoding of this value.  """
        raise NotImplementedError

    @abstractmethod
    def decode(self, buf):
        """ Decodes a buffer into the value for this object. """
        raise NotImplementedError


class ValueEncoder:
    @abstractmethod
    def encoded_len(self):
        """ The number of byte expected for in the encoding of this value.  """
        raise NotImplementedError

    @abstractmethod
    def encode(self, value):
        """ Decodes a buffer into the value for this object. """
        raise NotImplementedError


class ReadableObject(ContainedObject, ValueDecoder, metaclass=ABCMeta):
    def read(self):
        return self.controller.read_value(self)


class WritableObject(ContainedObject, ValueDecoder, ValueEncoder, metaclass=ABCMeta):
    def write(self, value):
        return self.controller.write_value(self, value)


class LongDecoder(ValueDecoder):
    def decode(self, buf):
        return ((((buf[0] * 256) + buf[1]) * 256) + buf[2]) * 256 + buf[3]

    def encoded_len(self):
        return 4


class ShortDecoder(ValueDecoder):
    def decode(self, buf):
        return buf[0] * 256 + buf[1]

    def encoded_len(self):
        return 2


class ByteDecoder(ValueDecoder):
    def decode(self, buf):
        return int(buf[0])

    def encoded_len(self):
        return 1


class BufferDecoder(ValueDecoder):
    def decode(self, buf):
        return buf


class BufferEncoder(ValueEncoder):
    def encode(self, value):
        return value


class ReadWriteBaseObject(ReadableObject, WritableObject):
    pass


class ReadWriteObject(ReadWriteBaseObject):
    def read(self):
        return self.controller.read_value(self)

    def write(self, value):
        self.controller.write_value(self, value)


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


class CurrentTicks(ReadableObject, LongDecoder):
    type_id = ObjectType.current_ticks


class BaseController:
    """ provides the operations common to all controllers.
    """

    def __init__(self, connector):
        self._root = RootContainer(self)
        self._sysroot = RootContainer(self)
        self.connector = connector

    def system_id(self):
        return SystemID(self, self._sysroot, 0)

    def initialize(self, id_service):
        id_obj = self.system_id()
        current_id = id_obj.read()
        if int(current_id[0]) == 0xFF:
            current_id = id_service()
        id_obj.write(current_id)
        return current_id

    def full_erase(self):
        # need profile enumeration - for now, just assume 4 profiles
        available = self.active_and_available_profiles()
        for p in available[1]:
            self.delete_profile(p)

    def read_value(self, obj: ReadableObject):
        data = self._fetch_data_block(self.connector.protocol.read_value, obj.id_chain, obj.encoded_len())
        return obj.decode(data)

    def write_value(self, obj: WritableObject, value):
        self._write_value(obj, value, self.connector.protocol.write_value)

    def delete_object(self, obj: ContainedObject):
        self._handle_error(self.connector.protocol.delete_object, obj.id_chain)

    def next_slot(self, container) -> int:
        return self._handle_error(self.connector.protocol.next_slot, container.id_chain)

    def create_profile(self):
        profile_id = self._handle_error(self.connector.protocol.create_profile)
        return self.profile_for(profile_id)

    def delete_profile(self, p: Profile):
        self._handle_error(self.connector.protocol.delete_profile, p.profile_id)

    def activate_profile(self, p: Profile):
        """ activates the given profile. if p is None, the current profile is deactivated. """
        self._handle_error(self.connector.protocol.activate_profile, Profile.id_for(p))

    def active_and_available_profiles(self):
        """
            returns a tuple - the first element is the active profile, or None if no profile is active.
            the second element is a sequence of profiles.
        """
        future = self.connector.protocol.list_profiles()
        data = BaseController.result_from(future)
        activate = self.profile_for(data[0])
        available = tuple([self.profile_for(x) for x in data[1:]])
        return activate, available

    def is_active_profile(self, p: Profile):
        active = self.active_and_available_profiles()[0]
        return False if not active else active.profile_id == p.profile_id

    def reset(self, erase_eeprom=False):
        if erase_eeprom:  # return the id back to the pool if the device is being wiped
            current_id = self.system_id().read()
            controller_id.return_id(current_id)
        self._handle_error(self.connector.protocol.reset, 1 if erase_eeprom else 0)

    def read_system_value(self, obj: ReadableObject):
        data = self._fetch_data_block(self.connector.protocol.read_system_value, obj.id_chain, obj.encoded_len())
        return obj.decode(data)

    def write_system_value(self, obj: WritableObject, value):
        self._write_value(obj, value, self.connector.protocol.write_system_value)

    def _write_value(self, obj: WritableObject, value, fn):
        encoded = obj.encode(value)
        data = self._fetch_data_block(fn, obj.id_chain, encoded)
        if data != encoded:
            raise FailedOperationError("could not write value")

    def create_object_current_ticks(self, container) -> CurrentTicks:
        return self._create_object(container, CurrentTicks)


    @property
    def root_container(self):
        return self._root

    def _create_object(self, container: Container, obj_class, data=None):
        if not data:
            data = []
        slot = self.next_slot(container)
        id_chain = container.id_chain_for(slot)
        self._handle_error(self.connector.protocol.create_object, id_chain, obj_class.type_id, data)
        return obj_class(self, container, slot)

    @staticmethod
    def _handle_error(fn, *args):
        future = fn(*args)
        error = BaseController.result_from(future)
        if error < 0:
            raise FailedOperationError("errorcode %d" % error)
        return error

    @staticmethod
    def _fetch_data_block(fn, *args):
        future = fn(*args)
        data = BaseController.result_from(future)
        if not data:
            raise FailedOperationError("no data")
        return data

    @staticmethod
    def result_from(future: FutureResponse):
        # todo - on timeout, unregister the future from the async protocol handler to avoid
        # a memory leak
        return None if future is None else future.value(timeout)

    def profile_for(self, profile_id):
        return Profile(self, profile_id) if profile_id >= 0 else None


class CrossCompileController(BaseController):
    """ additional options only available on the cross-compile """

