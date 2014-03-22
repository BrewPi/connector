import nose
from serial import Serial
import sys
from connector.integration_test.base_test import BaseControllerTestHelper
from connector.serialconn import SerialConnector
from connector.v03x import ArduinoController
from test.config import apply_module
import unittest

__author__ = 'mat'

arduino_serial_port = None
arduino_baud = None

apply_module(sys.modules[__name__], 2)

@unittest.skipUnless(arduino_serial_port, "arduino_serial not defined")
class ArduinoTestCase(BaseControllerTestHelper, unittest.TestCase):
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

