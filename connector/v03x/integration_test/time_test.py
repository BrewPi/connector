__author__ = 'mat'


from time import sleep

from hamcrest import greater_than, is_, assert_that, less_than

from connector.v03x.integration_test.base_test import BaseControllerTestHelper
from connector.v03x.time import ValueProfile, ValueProfileState

class SystemTimeTest(BaseControllerTestHelper):
    """ Tests the system time component. """
    def test_can_read_system_time(self):
        systime = self.c.system_time()
        sleep(0.01)
        time, scale = systime.read()
        assert_that(time, is_(greater_than(0)), "expected time > 0")
        assert_that(time, is_(less_than(60000)), "expected time < 60000")
        assert_that(scale, is_(1), "expected scale to be 1")
        sleep(0.1)
        time2, scale2 = systime.read()
        assert_that(time2, is_(greater_than(time+10)), "expected time > 10 since last check")
        assert_that(scale, is_(1), "expected scale to be 1")

    def test_can_stop_time(self):
        systime = self.c.system_time()
        original_time = 123000
        systime.write((original_time, 0))
        time, scale = systime.read()
        assert_that(time, is_(original_time), "expected time to remain unchanged")
        assert_that(scale, is_(0), "expected scale to be 0")
        systime.write((original_time+100, 0))
        time, scale = systime.read()
        assert_that(time, is_(original_time+100), "expected time +100")
        assert_that(scale, is_(0), "expected scale to be 0")


class ValueProfileTest(BaseControllerTestHelper):
    def test_constant_profile(self):
        sysProfile = self.setup_profile()
        state = ValueProfileState()
        valueProfile = self.c.create_object(ValueProfile, state)

