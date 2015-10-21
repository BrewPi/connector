from abc import abstractmethod
from conduit.base import Conduit
from protocol.factory import determine_protocol, UnknownProtocolError
from support.events import EventHook

__author__ = 'mat'


class ConnectorError(Exception):
    """ Inidcates an error condition with a connection. """
    pass


class ConnectionNotConnectedError(ConnectorError):
    """ Indicates a connection is in the disconnected state when a connection is required. """
    pass


class ConnectionNotAvailableError(ConnectorError):
    """ Indicates the connection is not available. """
    pass


class Connector():
    """ A connector provides the protocol (and conduit the protocol is transported over)
    """
    @property
    @abstractmethod
    def protocol(self):
        return None

    @property
    @abstractmethod
    def connected(self):
        """
        Determines if this connector is connected to it's underlying resource.
        :return: True if this connector is connected to it's underlying resource. False otherwise.
        :rtype: bool
        """
        return False

    @property
    @abstractmethod
    def conduit(self):
        """
        Retreives the conduit for this connection. If the connection is not connected, raises NotConnectedError
        :return:
        :rtype:
        """
        raise ConnectionNotConnectedError

    @property
    @abstractmethod
    def available(self):
        """ Determines if the underlying resource for this connector is available.
        :return: True if the resource is available and can be connected to.
        :rtype: bool
        """
        return False

    @abstractmethod
    def connect(self):
        """
        Connects this connector to the underlying resource. If the connection is already connected,
        this method returns silently. Raises ConnectionError if the connection cannot be established.
        :return:
        :rtype:
        """
        pass

    @abstractmethod
    def disconnect(self):
        pass


class ConnectorMonitorListener:

    @staticmethod
    def connection_available(connector: Connector):
        """ Notifies this listener that the given connection is available, but not connected. """
        pass

    @staticmethod
    def connection_connected(connector: Connector):
        """ Notifies this listener that the given connection has been established. """
        pass

    @staticmethod
    def connection_disconnected(connector: Connector):
        """ Notifies this listener that the given connection has been disconnected. """
        pass


class ConnectorMonitor:
    """ inspects a list of Connectors for changes.
    """

    def __init__(self, connectors: list):
        self.connectors = connectors

    def scan(self):
        for connector in self.connectors:
            if connector.available and not connector.connected:
                connector.connect()


class AbstractConnector(Connector):
    """ Manages the connection cycle, using a protocol sniffer to determine the protocol
        of the connected device. """

    def __init__(self):
        self.changed = EventHook()
        self._base_conduit = None
        self._conduit = None
        self._protocol = None

    @property
    def available(self):
        return False if self.connected else self._try_available()

    @property
    def connected(self):
        return self._protocol is not None and self._connected()

    def connect(self):
        if self.connected:
            return
        if not self.available:
            raise ConnectionNotAvailableError
        try:
            self._base_conduit = self._connect()
            self._conduit = self._base_conduit
            self._protocol = determine_protocol(self._conduit)
        except UnknownProtocolError as e:
            raise ConnectorError() from e
        finally:
            if not self._protocol:
                self.disconnect()

    def disconnect(self):
        if not self._conduit:
            return
        self._disconnect()
        if self._protocol:
            if hasattr(self._protocol, 'shutdown'):
                self._protocol.shutdown()
            self._protocol = None
        if self._conduit:
            self._conduit.close()
            self._conduit = None

    @abstractmethod
    def _connect(self) -> Conduit:
        """ Template method for subclasses to perform the connection.
            If connection is not possible, an exception should be thrown
        """
        raise NotImplementedError

    @abstractmethod
    def _try_available(self):
        """ Determine if this connection is available. This method is only called when
            the connection is disconnected.
        :return: True if the connection is available or False otherwise.
        :rtype: bool
        """
        raise NotImplementedError

    @abstractmethod
    def _disconnect(self):
        raise NotImplementedError

    @abstractmethod
    def _connected(self):
        raise NotImplementedError

    @property
    def conduit(self):
        self.check_connected()
        return self._conduit

    @property
    def protocol(self):
        self.check_connected()
        return self._protocol

    def check_connected(self):
        if not self.connected:
            raise ConnectionNotConnectedError
