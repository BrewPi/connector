import unittest
from unittest import TestCase
from unittest.mock import Mock

from hamcrest import assert_that, equal_to, is_, is_not, is_in, not_

from controlbox.conduit.base import Conduit
from controlbox.support.events import EventSource


class ControllerConnectionManager:
    """
    Keeps track of the sources and optional associated conduit+protocol handler.
    A source will not be opened by an enumerator while it's in the conduit manager (so source are tried once when connected and not again until reconnected.)
    """
    connected = "connected"
    disconnected = "disconnected"


    def __init__(self, sniffer):
        """
        :param sniffer A callable that takes a conduit and determines the protocol. Returns a protocol instance or None
        if the protocol is not recognised.
        """
        self._connections = dict()
        self._sniffer = sniffer
        self.events = EventSource()

    def disconnected(self, source):
        """ registers the given source as being disconnected. """
        if source in self._connections:
            data = self._connections[source]
            del self._connections[source]
            conduit, protocol = (None, None) if data is None else (data[0], data[1])
            self.events.fire(self, ControllerConnectionManager.disconnected, source, conduit, protocol)

    def connected(self, source, conduit=None):
        """ Notifies this manager that the given conduit is available as a possible controller connection.
            The manager attempts to sniff the protocol in the conduit.
            The source and conduit is remembered to avoid subsequent rettempts. """
        data = None
        protocol = None
        if conduit is not None:
            protocol = self._sniffer(conduit)
            if protocol is None:            # not recognised
                conduit.close()             # close the conduit so others can use it
            data = conduit, protocol
        self._connections[source] = data
        self.events.fire(self, ControllerConnectionManager.connected, source, conduit, protocol)
        return data

    @property
    def connections(self):
        return dict(self._connections)


class ControllerConnectionManagerTest(TestCase):

    def test_construction(self):
        sniffer = Mock()
        listener = Mock()
        sut = ControllerConnectionManager(sniffer)
        sut.events += listener
        assert_that(sut.connections, is_(equal_to(dict())))
        assert_that(sut._sniffer, equal_to(sniffer))
        assert_that(sut.events, is_not(None))
        sniffer.assert_not_called()
        listener.assert_not_called()

    def test_connected_no_conduit(self):
        sniffer = Mock()
        listener = Mock()
        sut = ControllerConnectionManager(sniffer)
        sut.events += listener
        sut.connected("myconn")
        assert_that(sut.connections, is_(equal_to({"myconn":None})))
        sniffer.assert_not_called()
        listener.assert_called_once_with(sut, ControllerConnectionManager.connected, "myconn", None, None)

    def test_connected_with_conduit_no_protocol(self):
        sniffer = Mock(return_value=None)
        listener = Mock()
        conduit = Conduit()
        conduit.close = Mock()
        sut = ControllerConnectionManager(sniffer)
        sut.events += listener
        result = sut.connected("myconn", conduit)
        assert_that(result, is_((conduit, None)))
        sniffer.assert_called_once_with(conduit)
        listener.assert_called_once_with(sut, ControllerConnectionManager.connected, "myconn", conduit, None)
        conduit.close.assert_called_once_with()

    def test_connected_conduit_with_protocol(self):
        protocol = object()
        sniffer = Mock(return_value=protocol)
        conduit = object()
        listener = Mock()
        sut = ControllerConnectionManager(sniffer)
        sut.events += listener
        result = sut.connected("myconn", conduit)
        assert_that(result, is_((conduit, protocol)))
        assert_that(sut.connections["myconn"], is_((conduit, protocol)))
        sniffer.assert_called_once_with(conduit)
        listener.assert_called_once_with(sut, ControllerConnectionManager.connected, "myconn", conduit, protocol)

    def test_disconnected_not_known(self):
        sut = ControllerConnectionManager(None)
        listener = Mock()
        sut.events += listener
        sut.disconnected("myconn")
        listener.assert_not_called()

    def test_connected_then_disconnected(self):
        protocol = object()
        sniffer = Mock(return_value=protocol)
        conduit = object()
        sut = ControllerConnectionManager(sniffer)
        sut.connected("myconn", conduit)
        assert_that("myconn", is_in(sut.connections))

        listener = Mock()
        sut.events += listener
        sut.disconnected("myconn")
        listener.assert_called_once_with(sut, ControllerConnectionManager.disconnected, "myconn", conduit, protocol)
        assert_that("myconn", not_(is_in(sut.connections)))


class SerialControllerEnumerator:
    """
    Enumerates local serial busses for connected controllers.

    - scan known serial ports (using pyserial) to get a set of available serial ports
     - difference this from previously scanned ports - determine any that have been disconnected (so next time they are connected we retry.)

    - from each port that is not already open (check with the conduit manager)
     - attempt to open
      - on success, pass the conduit and the source to the ConduitManager
      - on fail, pass the source and a failed flag to the conduit manager

    """


class WiFiControllerEnumerator:
    """
        Enumerates wifi:
        - zeroconf, bonjour, mDNS, TCP server?
        - each device announces its presence

        - "sniff" the conduit,
        - if it's a controller, post a controller connected event - keep the conduit open along with the protocol handler
        - connected controllers are maintained globally and are not sniffed again
        -


    - Unit testing
     - mock an enumerator and validate the various events are fired (TDD)

    Integration testing
     - setup with 2 serial controllers, and 2 wifi controllers
     - controller supports reset so we can force a disconnect

    """


if __name__ == '__main__':
    unittest.main()
