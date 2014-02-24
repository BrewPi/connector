from audioop import reverse
from concurrent.futures import ThreadPoolExecutor, Future
from queue import Queue, Empty
from conduit.base import Conduit
from conduit.test.async_test import AsyncConnectorTest
import serial
import unittest

from conduit.serial import serial_connector_factory

__author__ = 'mat'


# todo - factor out port to environment
port = "COM16"      # a regular working COM port (e.g. an arduino)
invalid_port = "ABC___not_found"

virtualPortPair = "COM7","COM8"     # pair of virtual ports connected as a null modem
baud = 57600

class ConnectorSerialTestCase(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        super().__init__(methodName)
        self.connection = None

    def setup(self):
        self.connection = None

    def tearDown(self):
        self.connection and self.connection.close()

    def test_factory_method_returns_callable(self):
        factory = serial_connector_factory(invalid_port, baud, timeout=1)
        assert callable(factory)

    def test_invalid_arguments_fail(self):
        factory = serial_connector_factory(invalid_port, baud, timeout=1)
        self.assertRaises(serial.SerialException, factory)

    def test_read_serial(self):
        factory = serial_connector_factory(port, baud, timeout=1)
        self.connection = factory()
        input = self.connection.input
        line = input.read()
        self.assertIsNotNone(line)

    def test_write_serial(self):
        factory = serial_connector_factory(port, baud, timeout=1)
        self.connection = factory()
        self.connection.output.write("abc".encode())

    @unittest.skip("cannot get writelines to work - raises TypeError: 'int' object is not iterable")
    def test_writelines_serial(self):
        factory = serial_connector_factory(port, baud, timeout=1)
        self.connection = factory()
        s = "abc".encode()
        self.connection.output.writelines(s)


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
