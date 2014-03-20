import sys
import serial
import unittest
from hamcrest import assert_that, equal_to, is_
from conduit.test.async_test import AsyncConnectorTest

from conduit.serial import serial_connector_factory, detect_port
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
        self.assertWriteRead("reverse direction\nline\n", self.connections[::-1])


if __name__ == '__main__':
    unittest.main()
