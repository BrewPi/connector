import sys
import unittest
from threading import Thread
from time import sleep

from brewpi.connector.controlbox.integration_test.base_test import BaseControllerTestHelper
from brewpi.connector.controlbox.integration_test.indirect_value_test import IndirectValueTest
from brewpi.connector.controlbox.integration_test.persistence_test import PersistentValueTest, PersistentChangeValueTest
from brewpi.connector.controlbox.integration_test.time_test import SystemTimeTest, ValueProfileTest
from hamcrest import assert_that, is_, starts_with, equal_to
from serial import Serial

from brewpi.controlbox.objects import ArduinoController
from controlbox.config.config import configure_module
from controlbox.connector.serialconn import SerialConnector

arduino_serial_port = None
arduino_baud = None

configure_module(sys.modules[__name__])


@unittest.skipUnless(arduino_serial_port, "arduino_serial not defined")
class SerialPortTestCase(unittest.TestCase):

    def test_mutithreaded_serial(self):
        s = Serial()
        s.setPort(arduino_serial_port)
        s.setBaudrate(arduino_baud)
        assert_that(s.isOpen(), is_(False),
                    "expected serial port to be initially closed")
        s.open()
        sleep(5)
        s.write(bytes(b'00\x0A'))  # null command

        self.serial = s
        t = Thread(target=self.async_read)
        t.setDaemon(True)
        t.start()

        t.join(10)
        assert_that(t.is_alive(), is_(False), "exepcted thread to terminate")

    def async_read(self):
        l = self.serial.readline()
        line = l.decode('utf-8')
        assert_that(line, starts_with(
            '['), "expected version string/protocol identifier")
        l = self.serial.readline()
        line = l.decode('utf-8')
        assert_that(line, is_(equal_to("00\n")),
                    "expected 00 command response")


@unittest.skipUnless(arduino_serial_port, "arduino_serial not defined")
class BaseArduinoTestCase:

    def __init__(self, name):
        super().__init__(name)
        self.initialize_id = True

    def create_connector(self):
        s = Serial()
        s.setPort(arduino_serial_port)
        s.setBaudrate(arduino_baud)
        return SerialConnector(s)

    def create_controller(self):
        return ArduinoController(self.connector)


class ArduinoTestCase(BaseArduinoTestCase, BaseControllerTestHelper, unittest.TestCase):
    __test__ = True


class ArduinoSysTimeTestCase(BaseArduinoTestCase, SystemTimeTest, ValueProfileTest):
    __test__ = True


class ArduinoIndirectValueTestCase(BaseArduinoTestCase, IndirectValueTest):
    __test__ = True


class ArduinoPersistenceTestCase(BaseArduinoTestCase, PersistentValueTest, PersistentChangeValueTest):
    __test__ = True
