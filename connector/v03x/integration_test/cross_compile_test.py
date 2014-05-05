import os
import sys
import unittest

from connector.v03x.integration_test.base_test import GeneralControllerTests
from connector.v03x.integration_test.indirect_value_test import IndirectValueTest
from connector.v03x.integration_test.time_test import SystemTimeTest, ValueProfileTest
from connector.processconn import ProcessConnector
from connector.v03x.objects import CrossCompileController
from test.config import apply_module


__author__ = 'mat'

cross_compile_exe = None

apply_module(sys.modules[__name__], 3)


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


class CrossCompileTestCase(BaseCrossCompileTestCase, GeneralControllerTests):
    __test__ = True


class CrossCompileSysTimeTestCase(BaseCrossCompileTestCase, SystemTimeTest, ValueProfileTest):
    __test__ = True

class CrossCompileIndirectValueTestCase(BaseCrossCompileTestCase, IndirectValueTest):
    __test__ = True
