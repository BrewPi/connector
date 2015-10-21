
__author__ = 'mat'


from time import sleep

from hamcrest import greater_than, is_, assert_that, less_than, equal_to

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
        assert_that(time2, is_(greater_than(time + 10)),
                    "expected time > 10 since last check")
        assert_that(scale, is_(1), "expected scale to be 1")

    def test_can_stop_time(self):
        systime = self.c.system_time()
        original_time = 123000
        systime.write((original_time, 0))
        time, scale = systime.read()
        assert_that(time, is_(original_time),
                    "expected time to remain unchanged")
        assert_that(scale, is_(0), "expected scale to be 0")
        systime.write((original_time + 100, 0))
        time, scale = systime.read()
        assert_that(time, is_(original_time + 100), "expected time +100")
        assert_that(scale, is_(0), "expected scale to be 0")

    def test_scale_from_last_setpoint(self):
        """ Verifies that the time scaling happens from when the scale is changed.
        """
        systime = self.c.system_time()
        time1 = 60000
        value = systime.set(time1, 0)
        value2 = systime.read()
        assert_that(value, is_(equal_to(value2)))
        time, scale = value2
        assert_that(time, is_(time1))
        assert_that(scale, is_(0))
        sleep(0.1)
        value3 = systime.read()
        assert_that(value3, is_(equal_to(value2)))
        value4 = systime.set(None, 1)
        assert_that(value4, is_(equal_to((60000, 1))))
        sleep(0.1)
        time, scale = systime.read()
        assert_that(scale, is_(1))
        assert_that(time, greater_than(60090))
        assert_that(time, less_than(60200))

    def test_create_current_ticks(self):
        """ when a profile is created and
            when a CurrentTicks() object is created
                then the returned value is > 0
            and when waiting 10 ms then the new value is at least 10 ms larger
        """
        self.setup_profile()
        host = self.controller.root_container
        current_ticks = self.controller.create_current_ticks(host)
        ticks = current_ticks.read()
        assert_that(ticks, is_(greater_than(0)), "expected ticks > 0")
        sleep(0.1)
        ticks2 = current_ticks.read()
        assert_that(ticks2 - ticks, is_(greater_than(90)))


class ValueProfileTest(BaseControllerTestHelper):

    def test_constant_profile(self):
        p = self.setup_profile()
        state = ValueProfileState()
        valueProfile = self.c.create_object(ValueProfile, state)
