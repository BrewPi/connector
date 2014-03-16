from abc import abstractmethod, ABCMeta
from protocol.async import FutureResponse

__author__ = 'mat'

"""
"""

timeout = 1000  # long enough to allow debugging, but not infinite so that build processes will eventually terminate


class FailedOperationError(Exception):
    pass


class BaseControllerObject():
    def __init__(self, controller):
        self.controller = controller


class ControllerObject(metaclass=ABCMeta, BaseControllerObject):
    @property
    @abstractmethod
    def id_chain(self):
        """  all controller objects have an id chain that describes their location and id in the system. """
        raise NotImplementedError


class Container:
    pass


class BaseController:
    pass


class ContainedObject(ControllerObject):
    """ An object in a container. Contained objects have a slot that is the id relative to the container
        the object is in. The full id_chain is the container's id plus the object's slot in the container.
    """

    def __init__(self, controller: BaseController, container: Container, slot: int):
        """
            :param controller:
            :type controller:
            :param container:   The container hosting this object. Will be None if this is the root container.
            :type container:
            :param slot:
            :type slot:
            :return:
            :rtype:
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


class _ContainerTraits:
    @abstractmethod
    def id_chain_for(self, slot):
        raise NotImplementedError


class Container(ContainedObject, _ContainerTraits):
    def id_chain_for(self, slot):
        return self.container.id_chain + (slot,)


class RootContainer(ControllerObject, _ContainerTraits):
    """ A root container is the top-level container - it is not contained in any container. """

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


class Profile(BaseControllerObject):
    """ represents a profile. """

    def __init__(self, controller, profile_id):
        super().__init__(controller)
        self.profile_id = profile_id

    def activate(self):
        self.controller.activate_profile(self)

    def deactivate(self):
        self.controller.deactivate_profile(self)

    @property
    def active(self):
        return self.controller.is_active(self)


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


class ReadableObject(metaclass=ABCMeta, ContainedObject, ValueDecoder):
    def read(self):
        return self.controller.read_value(self)


class ShortDecoder(ValueDecoder):
    def decode(self, buf):
        return int(buf[0]) << 8 + buf[1]

    def encoded_len(self):
        return 2


class CurrentTicks(ReadableObject, ShortDecoder):
    type_id = ObjectType.current_ticks


class BaseController:
    """ provides the operations common to all controllers.
    """

    def __init__(self, connector):
        self._root = RootContainer(self)
        self.connector = connector

    def full_erase(self):
        # need profile enumeration - for now, just assume 4 profiles
        for x in range(0, 4):
            self.delete_profile(x)

    def read_value(self, obj: ReadableObject):
        data = self._fetch_data_block(self.connector.protocol.read_value, obj.id_chain, obj.encoded_len())
        return obj.decode(data)

    def next_slot(self, container) -> int:
        return self._handle_error(self.connector.protocol.next_slot, container.id_chain)

    def create_profile(self):
        profile_id = self._handle_error(self.connector.protocol.create_profile)
        return self.profile_for(profile_id)

    def delete_profile(self, p: Profile):
        self._handle_error(self.connector.protocol.delete_profile, p.profile_id)

    def activate_profile(self, p: Profile):
        """ activates the given profile. """
        self._handle_error(self.connector.protocol.activate_profile, p.profile_id)

    def available_profiles(self):
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
        active = self.available_profiles()[0]
        return False if not active else active.profile_id==p.profile_id

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
        return None if future is None else future.value(timeout)

    def profile_for(self, profile_id):
        return Profile(self, profile_id) if profile_id >= 0 else None


class CrossCompileController(BaseController):
    """ additional options only available on the cross-compile """