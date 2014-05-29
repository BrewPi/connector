from hamcrest import assert_that, is_, not_none, equal_to, is_not
from connector.v03x.controller import DynamicContainer
from connector.v03x.integration_test.base_test import BaseControllerTestHelper

__author__ = 'mat'

import unittest


class ControlLoopTest(BaseControllerTestHelper):
    def setUp(self):
        super().setUp()
        self.p = self.setup_profile()

    def test_first_object_is_slot_1(self):
        o = self.c.create_object(DynamicContainer)
        assert_that(o.slot, is_(1), "expected first object to be at slot 1 in ControllLoopContainer")

    def assert_default_loop_config(self, loop):
        assert_that(loop, is_(not_none()), "expected control loop for object")
        state = loop.value
        assert_that(state, is_(not_none()), "expected control loop config")
        assert_that(state.period, is_(0), "expected default period 0")
        assert_that(state.log_period, is_(0), "expected default log_period 0")
        assert_that(state.enabled, is_(False), "expected default loop to be disabled")

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
        config = loop.value
        config.period = 60
        config.log_period = 2
        config.enabled = True
        loop.value = config
        config2 = loop.value
        assert_that(config2 is config, is_(False), "expected a distinct instance")
        assert_that(config2, is_(equal_to(config)))


    def test_empty_root_container_has_size_1(self):
        """ The size of the root container is 1, which is just the config container. """

    def test_empty_root_container_item_0_is_null(self):
        """ The size of the config container is 1, although the object is NULL. """

    def test_create_object_slot_0_in_root_fails_gracefully(self):
        """ Attempts to create an object at slot 0 in the root container. This should fail gracefully. """

    def test_loop_counter(self):
        """ sets a loop to run with a period of 2 ms, running for ca. 1/10th of a second. The system time is stopped and
            the current time used to determine the expected number of iterations of the loop. """

    def test_stop_loop_counter(self):
        """ validates that a loop counter can be started and then stopped. Stopping the counter stops incrementing the
            counter and stops posting logs. """


    def test_loop_persist(self):
        """ validates that the enabled, loop period and logging flags are correctly persisted and reinstated on reset. """


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



if __name__ == '__main__':
    unittest.main()
