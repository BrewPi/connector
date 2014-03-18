from operator import and_
from time import sleep
from hamcrest import greater_than, is_, assert_that, equal_to, less_than, is_not
import sys
from conduit.base import RedirectConduit
from connector import controller_id
from connector.integration_test.base_test import BaseControllerTestHelper
from connector.processconn import ProcessConnector
from connector.v03x import CrossCompileController
from protocol.async import AsyncHandler

__author__ = 'mat'

""" Uses the cross-compiled "arduino" code to test the
"""
import unittest

cross_compile_exe = "R:\\dev\\brewpi\\brewpi-avr\\brewpi_sim\dist\\Debug\\MinGW-Windows\\brewpi_sim.exe"

def build_controller():
    c = ProcessConnector(cross_compile_exe, None)
    # c.build_conduit = lambda x: RedirectConduit(x, sys.stdout)
    c.connect()
    c = CrossCompileController(c)
    c.connector.protocol.start_background_thread()
    return c


class CrossCompileTestCase(BaseControllerTestHelper, unittest.TestCase):
    def __init__(self, name):
        super().__init__(name)
        self.initialize_id = True

    def create_controller(self):
        c = build_controller()
        if self.initialize_id:
            c.initialize(self.id_service())
        return c

    def test_create_current_ticks(self):
        """ when a profile is created and
            when a CurrentTicks() object is created
                then the returned value is > 0
            and when waiting 10 ms then the new value is at least 10 ms larger
        """
        self.setup_profile()
        host = self.controller.root_container
        current_ticks = self.controller.create_object_current_ticks(host)
        ticks = current_ticks.read()
        assert_that(ticks, is_(greater_than(0)), "expected ticks > 0")
        sleep(0.01)
        ticks2 = current_ticks.read()
        assert_that(ticks2 - ticks, is_(greater_than(9)))



if __name__ == '__main__':
    unittest.main()
