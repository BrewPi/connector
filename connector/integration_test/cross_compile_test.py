from time import sleep
from hamcrest import greater_than, is_, assert_that, equal_to, less_than, is_not
import sys
from connector.integration_test.base_test import BaseControllerTestHelper
from connector.processconn import ProcessConnector
from connector.v03x import CrossCompileController
from test.config import apply_module

__author__ = 'mat'

""" Uses the cross-compiled "arduino" code to test the
"""
import unittest

cross_compile_exe = None

apply_module(sys.modules[__name__])

@unittest.skipUnless(cross_compile_exe, "cross-compile exe not defined")
class CrossCompileTestCase(BaseControllerTestHelper, unittest.TestCase):
    def __init__(self, name):
        super().__init__(name)

    def create_connector(self):
        return ProcessConnector(cross_compile_exe, None)

    def create_controller(self):
        return CrossCompileController(self.connector)

if __name__ == '__main__':
    unittest.main()
