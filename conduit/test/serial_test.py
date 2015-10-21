import sys
import serial
import unittest
from mockito import mock, verifyNoMoreInteractions, verify, any, when
from hamcrest import assert_that, equal_to, is_, has_length
from conduit.test.async_test import AsyncConnectorTest

from conduit.serial_conduit import detect_port, SerialWatchdog, serial_connector_factory
from conduit.watchdog import ResourceUnavailableEvent, ResourceAvailableEvent
from test.config import apply_module

__author__ = 'mat'

port = None
virtualPortPair = None
invalid_port = "ABC___not_found"
arduino_port_detect = None
baud = 57600

apply_module(sys.modules[__name__])


class ConnectorSerialTestCase(unittest.TestCase):

    def __init__(self, methodName='runTest'):
        super().__init__(methodName)
        self.connection = None

    def setup(self):
        self.connection = None

    def tearDown(self):
        self.connection and self.connection.close()

    def test_detect_port_given(self):
        assert_that(detect_port("COM2"), is_(equal_to("COM2")))

    @unittest.skipUnless(arduino_port_detect, "arduino_port_detect not defined")
    def test_detect_port_not_given(self):
        assert_that(detect_port("auto"), is_(equal_to(arduino_port_detect)))

    test_detect_port_not_given.os = 'windows'

    def test_factory_method_returns_callable(self):
        factory = serial_connector_factory(invalid_port, baud, timeout=1)
        assert callable(factory)

    def test_invalid_arguments_fail(self):
        factory = serial_connector_factory(invalid_port, baud, timeout=1)
        self.assertRaises(serial.SerialException, factory)

    @unittest.skipUnless(port, "arduino port not defined")
    def test_read_serial(self):
        p = detect_port(port)
        factory = serial_connector_factory(p, baud, timeout=1)
        self.connection = factory()
        input = self.connection.input
        line = input.read()
        self.assertIsNotNone(line)

    @unittest.skipUnless(port, "arduino port not defined")
    def test_write_serial(self):
        p = detect_port(port)
        factory = serial_connector_factory(p, baud, timeout=1)
        self.connection = factory()
        self.connection.output.write("abc".encode())

    @unittest.skip("cannot get writelines to work - raises TypeError: 'int' object is not iterable")
    def test_writelines_serial(self):
        factory = serial_connector_factory(port, baud, timeout=1)
        self.connection = factory()
        s = "abc".encode()
        self.connection.output.writelines(s)


@unittest.skipUnless(virtualPortPair, "need virtual serial ports defined")
class VirtualPortSerialTestCase(AsyncConnectorTest, unittest.TestCase):

    def createConnections(self):
        return [(lambda port: serial_connector_factory(port, baud, timeout=0.1)())(p) for p in virtualPortPair]

    def test_connections_are_open(self):
        for c in self.connections:
            self.assertTrue(c.open, "connection %s should be open" % c)

    def test_comms(self):
        self.assertWriteRead("some line\nand another", self.connections)
        self.assertWriteRead("more stuff\n", self.connections)
        self.assertWriteRead("reverse direction\nline\n",
                             self.connections[::-1])


arduino_device = (r"Arduino Leonardo", r"USB VID:PID=2341:8036")


class CallableMock(object):
    """ a work-around for mocks not being callable. https://code.google.com/p/mockito-python/issues/detail?id=5 """

    def __init__(self, mock):
        self.mock = mock

    def __call__(self, *args, **kwargs):
        return self.mock.__call__(*args, **kwargs)

    def __getattr__(self, method_name):
        return self.mock.__getattr__(method_name)


def verify_disconnected(mock):
    verify(mock).__exit__()


def verify_connected(mock):
    verify(mock).__enter__()


class SerialWatchdogTest(unittest.TestCase):

    def setUp(self):
        self.sut = SerialWatchdog(self.mock_connection)
        self.listener = mock()
        self.sut.listeners += CallableMock(self.listener)
        self.connections = {}

    def mock_connection(self, port, device):
        """ a mock factory to create connections. """
        m = mock()
        self.connections[port] = m
        return m

    def test_unknown_device_connected(self):
        """ simulates connection of an unknown device """
        device = ('test_port', 'mydevice', 'abc')
        self.sut.update_ports((device,))
        verifyNoMoreInteractions(self.listener)  # event listener not called
        assert_that(self.connections, has_length(0), "expected no connections")

    def test_device_connected(self):
        device = ('test_port', arduino_device[0], arduino_device[1])
        self.sut.update_ports((device,))
        verify(self.listener, 1).__call__(any(ResourceAvailableEvent))
        assert_that(self.connections, has_length(1),
                    "expected only one connection")
        verify_connected(self.connections['test_port'])

    def test_device_disconnected(self):
        device = ('test_port', arduino_device[0], arduino_device[1])
        self.sut.update_ports((device,))
        self.sut.update_ports(tuple())
        verify(self.listener, 1).__call__(any(ResourceAvailableEvent))
        verify(self.listener, 1).__call__(any(ResourceUnavailableEvent))
        assert_that(self.connections, has_length(1),
                    "expected only one connection")
        verify_connected(self.connections['test_port'])
        verify_disconnected(self.connections['test_port'])

    def test_device_changed(self):
        device = ('test_port', arduino_device[0], arduino_device[1])
        self.sut.update_ports((device,))
        test_device = ('test_port', 'test_device', 'test_device')
        self.sut.update_ports((test_device,))
        verify(self.listener, 1).__call__(any(ResourceAvailableEvent))
        verify(self.listener, 1).__call__(any(ResourceUnavailableEvent))
        assert_that(self.connections, has_length(1),
                    "expected only one connection")
        verify_connected(self.connections['test_port'])
        verify_disconnected(self.connections['test_port'])

    def test_multiple_connections(self):
        device = ('test_port', arduino_device[0], arduino_device[1])
        device2 = ('test_port2', arduino_device[0], arduino_device[1])
        self.sut.update_ports((device, device2))
        test_device = ('test_port', 'test_device', 'test_device')
        self.sut.update_ports((device2, test_device))
        assert_that(self.connections, has_length(2),
                    "expected two connections")
        verify(self.listener, 2).__call__(any(ResourceAvailableEvent))
        verify(self.listener, 1).__call__(any(ResourceUnavailableEvent))
        verify_connected(self.connections['test_port'])
        verify_disconnected(self.connections['test_port'])
        verify_connected(self.connections['test_port2'])
