"""
The API provided by the connector
"""
from brewpi.stateful.cbox import OneWireBus, PinSwitchesCollection, SwitchesCollection
from brewpi.stateful.cbox import TempSensorsCollection
from controlbox.stateful.api import Profile, RootContainer, ControlboxObject


class EventSource:
    def add_listener(self, listener):
        """adds a listener to this event source"""

    def remove_listener(self, listener):
        """removes a listener from this event source"""


class ControlboxController(EventSource):
    # the events are stateless controlbox events that describe object lifetime events
    # and state change events

    def system_container(self) -> RootContainer:
        """the system container for the controller."""

    def active_profile(self) -> Profile:
        """the current active profile. Will be None if no profile is active"""
        """todo - want this to be observable."""

    def create_profile(self) -> Profile:
        """create a new empty profile"""

    def profiles(self):
        """provides an observable set of Profiles that is updated as profiles are created and remoed."""


class ObservableSet(EventSource):
    """ provides a iterable of items and the ability to listen to them """


class ControllersSet(ObservableSet):
    """Contains possibly a mixed set of types for the different controllers available. """


class BrewpiConnector:

    def __init__(self, config):
        """
        :param config: configuration of the connector. has these keys
            discovery: a list of {type: t, propery:value} values describing the different types of
            ways controllers can be discovered.
                { type: serial }
                { type: executable, path: <path> }
                { type: mdns }
        """

    def controllers(self) -> ControllersSet:
        """ Retrieves an observable set of controllers. As controllers are detected or disconnected
         the set changes. """

    def shutdown(self):
        """Disconnects all controllers and stops controller discovery.
        :return:
        """

    def startup(self):
        """starts controller discovery to begin detecting controllers and maintaining their state.
        :return:
        """


class OneWireTemperatureSensor(ControlboxObject):
    pass


class OneWireActuator(ControlboxObject):
    pass


class PinActuator(ControlboxObject):
    pass

# these are installed devices. Just here for the API spec, but will be


class Device:
    def __init__(self, app, installed_type):
        self.app = app
        self.installed_type = installed_type

    def install(self):
        self.installed_type.install(self, self.app)


class TempSensorDevice(Device):
    def __init__(self, app, installed_type, initial_value=None):
        super().__init__(app, installed_type)
        self._value = None

    @property
    def value(self):
        return self._value


class AvailableOneWireTemperatureSensor(TempSensorDevice):
    """
    A temperature sensor that is available on the bus, but is not part of the installed temperature sensors.
    """
    def __init__(self, app):
        super().__init__(app, OneWireTemperatureSensor)


class AnalogInputTemperatureSensor(TempSensorDevice):
    pass


class AvailableActuator(Device):
    def __init__(self, app, installed_type, initial_value=None):
        super().__init__(app, installed_type)
        self._value = None

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value


class AvailablePinActuator(Device):
    def __init__(self, app):
        super().__init__(app, PinActuator)


class BrewpiApplication:
    """Knows about the specifics of the brewpi application, such as the location of well known objects"""

    @classmethod
    def as_brewpi_profile(self, Profile) -> "BrewpiApplication":
        """determines if the given profile is a brewpi profile.

            If it is, a BrewpiApplication instance is returned. If not, None is returned. """

    def installed_temp_sensors(self) -> TempSensorsCollection:
        """ retrieves the collection of temperature sensor objects installed in the system.
        Temp sensors are stored in a dedicated container.
        todo - what's the use case for this? """

    def installed_switches(self) -> SwitchesCollection:
        """
        The actuators installed in the system
        Actuators are stored in a dedicated container.
        :return:
        """

    def unassigned_temp_sensors(self):
        """finds the installed temperature sensors that are not assigned to a PID. """

    def unassigned_actuators(self):
        """finds the installed actuators that are not assigned to a PID. """

    # hardware
    def onewire_bus(self, id=None) -> OneWireBus:
        """ retrieves the onewire bus for the given ID. The default ID returns the default OneWire bus"""

    def pin_actuators_container(self) -> PinSwitchesCollection:
        """ retrieves the fixed collection of build-in GPIO switches. May be empty """

    # devices
    def available_temp_sensors(self):
        """ determines all temp sensors that are available for installation.
        Returns TempSensor objects that are transient. The value can be read, but the sensor is
        not installed in the system until
        """

    def available_switches(self):
        """ determines all temp sensors on the bus that are available for installation """

    def install(self, device):
        """installs a device in the system. This returns the object representing the installed device. """

    # end of devices

    def pids(self) -> ObservableSet:
        """ retrieves the set of pids in the system """
