from audioop import reverse
from concurrent.futures import ThreadPoolExecutor, Future
import os
from queue import Queue, Empty
import string
from conduit.base import Conduit
from conduit.test.async_test import AsyncConnectorTest
import serial
import unittest

from conduit.serial import serial_connector_factory

__author__ = 'mat'

# todo - factor out port to environment
port = os.environ.get('TEST_SERIAL_PORT')
virtualPortPairStr = os.environ.get('TEST_VIRTUAL_PAIR')      # pair of virtual ports connected as a null modem

virtualPortPair = None
if virtualPortPairStr:
    virtualPortPair = string.split(virtualPortPairStr, ",")

invalid_port = "ABC___not_found"
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

    @unittest.skipIf(not port, "arduino port not defined")
    def test_read_serial(self):
        factory = serial_connector_factory(port, baud, timeout=1)
        self.connection = factory()
        input = self.connection.input
        line = input.read()
        self.assertIsNotNone(line)

    @unittest.skipIf(not port, "arduino port not defined")
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
