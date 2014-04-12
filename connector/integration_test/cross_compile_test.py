import os
import sys
from connector.integration_test.base_test import GeneralControllerTests
from connector.integration_test.time_test import SystemTimeTest
from connector.processconn import ProcessConnector
from connector.v03x.objects import CrossCompileController
from test.config import apply_module
import unittest

__author__ = 'mat'

cross_compile_exe = None

apply_module(sys.modules[__name__], 2)


@unittest.skipUnless(cross_compile_exe, "cross-compile exe not defined")
class BaseCrossCompileTestCase:
    """ Uses the cross-compiled "arduino" code to test the main functionality of the v03x connector. """
    def __init__(self, name):
        super().__init__(name)
        setattr(self, name, super().__getattribute__(name))

    def create_connector(self):
        return ProcessConnector(os.path.expanduser(cross_compile_exe), None)

    def create_controller(self):
        return CrossCompileController(self.connector)


class CrossCompileTestCase(BaseCrossCompileTestCase, GeneralControllerTests, unittest.TestCase):
    pass


class CrossCompileSysTimeTestCase(BaseCrossCompileTestCase, SystemTimeTest, unittest.TestCase):
    pass
