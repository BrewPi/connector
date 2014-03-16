from time import sleep
from hamcrest import greater_than, is_, assert_that
from connector.integration_test.base_test import BaseTestCase
from connector.processconn import ProcessConnector
from connector.v03x import CrossCompileController
from protocol.async import AsyncHandler

__author__ = 'mat'

""" Uses the cross-compiled "arduino" code to test the
"""
import unittest


cross_compile_exe = "R:\\dev\\brewpi\\brewpi-avr\\brewpi_sim\dist\\Debug\\MinGW-Windows\\brewpi_sim.exe"



class CrossCompileTestCase(BaseTestCase):

    def create_controller(self):
        c = ProcessConnector(cross_compile_exe, None)
        c.connect()
        return CrossCompileController(c)


    def test_create_current_ticks(self):
        self.setup_profile()
        host = self.controller.root_container
        current_ticks = self.controller.create_object_current_ticks(host)
        ticks = current_ticks.read()
        assert_that(ticks, is_(greater_than(0)), "expected ticks > 0")
        sleep(0.01)
        ticks2 = current_ticks.read()
        assert_that(ticks2-ticks, is_(greater_than(9)))



if __name__ == '__main__':
    unittest.main()
