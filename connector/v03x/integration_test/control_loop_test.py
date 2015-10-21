from time import sleep
from hamcrest import assert_that, is_, not_none, equal_to, is_not, calling, raises, has_length, all_of, greater_than, \
    less_than
from nose.plugins.attrib import attr
from connector.v03x.controller import DynamicContainer, ControllerLoopState, FailedOperationError
from connector.v03x.integration_test.base_test import BaseControllerTestHelper

__author__ = 'mat'


@attr(fixture='v03x')
class ControlLoopTest(BaseControllerTestHelper):

    def setUp(self):
        super().setUp()
        self.p = self.setup_profile()
        self.log_events = []
        self.c.log_events += lambda x: self.log_events.append(x)

    def test_first_object_is_slot_1(self):
        o = self.c.create_object(DynamicContainer)
        assert_that(o.slot, is_(
            1), "expected first object to be at slot 1 in ControlLoopContainer")

    def assert_default_loop_config(self, loop):
        assert_that(loop, is_(not_none()), "expected control loop for object")
        state = loop.value
        assert_that(state, is_(not_none()), "expected control loop config")
        assert_that(state._period, is_(0), "expected default period 0")
        assert_that(state._log_period, is_(0), "expected default log_period 0")
        assert_that(state._enabled, is_(False),
                    "expected default loop to be disabled")

    def test_new_loop_config_is_set_to_default(self):
        """  asserts that a control loop starts off with the correct default config. """
        o = self.c.create_object(DynamicContainer)
        root = self.c.root_container
        loop = root.configuration_for(o)
        self.assert_default_loop_config(loop)

    def test_replace_loop_config_reverts_to_default(self):
        """ asserts that replacing the object at a given index in the container resets the control loop config. """
        o = self.c.create_object(DynamicContainer)
        root = self.c.root_container
        loop = root.configuration_for(o)
        config = loop.value
        config.period = 60
        config.log_period = 2
        config.enabled = True
        o = self.c.create_object(DynamicContainer, slot=o.slot)
        loop = root.configuration_for(o)
        self.assert_default_loop_config(loop)

    def test_set_loop_values(self):
        """ sets loop config values and verifies they are maintained """
        o = self.c.create_object(DynamicContainer)
        root = self.c.root_container
        loop = root.configuration_for(o)
        config = ControllerLoopState(True, 2, 60)
        loop.value = config
        config2 = loop.value
        assert_that(config2 is config, is_(False),
                    "expected a distinct instance")
        assert_that(config2, is_(equal_to(config)))

    def test_empty_root_container_has_size_1(self):
        """ The size of the root container is 1, which is just the config container. """
        assert_that(self.c.next_slot(self.c.root_container), is_(1))

    def test_empty_root_container(self):
        assert_that([x for x in self.c.list_objects(self.c.current_profile)], has_length(
            0), "expected no objects in the empty container")

    def test_create_object_slot_0_in_root_fails_gracefully(self):
        assert_that(calling(self.c.create_object).with_args(
            DynamicContainer, slot=0), raises(FailedOperationError))

    def test_logging_disabled(self):
        self.collect_logs(True, 0, 10)
        sleep(0.1)
        assert_that(self.log_events, has_length(0), "expected no logs")

    def test_logging_enabled(self):
        """ sets a loop to run with a period of 2 ms, running for ca. 1/10th of a second. The system time is stopped and
            the current time used to determine the expected number of iterations of the loop. """
        loop = self.collect_logs(True, 1, 10)
        sleep(0.1)
        # the exact number is 10 but fudge a bit for timing
        # inaccuracies/latency etc.
        assert_that(self.log_events, has_length(
            all_of(greater_than(5), less_than(12))), "expected about 10 logs")

    def test_logging_stop_loop(self):
        """ sets a loop to run with a period of 2 ms, running for ca. 1/10th of a second. The system time is stopped and
            the current time used to determine the expected number of iterations of the loop. """
        loop = self.collect_logs(True, 1, 10)
        sleep(0.1)
        loop.value = ControllerLoopState(enabled=False)
        count = len(self.log_events)
        assert_that(count, all_of(greater_than(5), less_than(12)),
                    "expected about 10 logs")
        sleep(0.2)
        # the exact number is 10 but fudge a bit for timing
        # inaccuracies/latency etc.
        assert_that(len(self.log_events), is_(count))

    def test_logging_stop_log(self):
        """ sets a loop to run with a period of 2 ms, running for ca. 1/10th of a second. The system time is stopped and
            the current time used to determine the expected number of iterations of the loop. """
        loop = self.collect_logs(True, 1, 10)
        sleep(0.1)
        loop.value = ControllerLoopState(log_period=0)
        sleep(0.2)
        # the exact number is 10 but fudge a bit for timing
        # inaccuracies/latency etc.
        assert_that(self.log_events, has_length(
            all_of(greater_than(5), less_than(12))), "expected about 10 logs")

    def init_logs(self):
        o = self.c.create_object(DynamicContainer)
        root = self.c.root_container
        loop = root.configuration_for(o)
        return loop

    def collect_logs(self, enabled, log_period, period):
        loop = self.init_logs()
        assert_that(self.log_events, has_length(0), "expected no logs")
        loop.value = ControllerLoopState(enabled, log_period, period)
        return loop

    def test_stop_loop_counter(self):
        """ validates that a loop counter can be started and then stopped. Stopping the counter stops incrementing the
            counter and stops posting logs. """

    def test_loop_persist(self):
        """ validates that the enabled, loop period and logging flags are correctly persisted and reinstated on reset. """
        o = self.c.create_object(DynamicContainer)
        root = self.c.root_container
        loop = root.configuration_for(o)
        loop.value = ControllerLoopState(False, 5, 0xbb8)   # 3000
        assert_that(loop.value, is_(ControllerLoopState(False, 5, 3000)))
        self.reset()
        assert_that(loop.value, is_(ControllerLoopState(False, 5, 3000)))


class ControlLoopInterleavedTest(BaseControllerTestHelper):
    """ A Test which sets up control loops and captures logs for each control loop. This allows the time for each log
        to be reported, the controller index, and the values of the contained objects. """

    def test_two_loop_counters_same_period(self):
        """ starts two interleaved loop counters, one with a period of 2ms, the other with a period of 4ms. """

    def test_two_loop_counters(self):
        """ starts two interleaved loop counters, one with a period of 2ms, the other with a period of 4ms. """

    def test_two_loop_counters_log_one(self):
        """ starts two interleaved loop counters, one with a period of 2ms, the other with a period of 4ms. """

    def test_two_loop_counters_log_both(self):
        """ starts two interleaved loop counters, one with a period of 2ms, the other with a period of 4ms, verified
            that each loop logs the correct values. """
