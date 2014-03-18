from abc import abstractmethod, ABCMeta
from operator import and_
from hamcrest import assert_that, equal_to, is_, greater_than, less_than, calling, raises, is_not, all_of
from connector import controller_id
from connector.v03x import BaseController, FailedOperationError, Profile

__author__ = 'mat'

import unittest


def profile_id_range():
    return range(0,4)

class BaseControllerTestHelper(metaclass=ABCMeta):
    def initialize_controller(self):
        self.controller = self.create_controller()
        self.protocol = self.controller.connector.protocol    # so we can access the protocol when the conduit is disconnected

    def setUp(self):
        """ subclass creates the controller. Ensures the controller has no profiles defined."""
        self.initialize_controller()
        self.controller.full_erase()
        act = self.c.active_and_available_profiles()
        assert_that(act[0], is_(None), "no profile should be loaded by default")
        assert_that(len(act[1]), is_(0), "no profiles created by default")

    def id_service(self):
        return controller_id.simple_id_service

    def discard_controller(self):
        self.controller.connector.disconnect()
        self.protocol.stop_background_thread()

    def tearDown(self):
        self.controller.reset(True)
        self.discard_controller()

    def reset(self, erase_eeprom=False):
        """ allows for a controller reset mid-test """
        self.controller.reset(erase_eeprom)
        self.discard_controller()
        self.initialize_controller()

    def setup_profile(self):
        profile = self.c.create_profile()
        profile.activate()
        assert_that(profile.is_active, is_(True))
        return profile

    @property
    def c(self)->BaseController:    # some type hinting for the IDE
        return self.controller

    def test_has_assigned_id(self):
        id = self.c.system_id().read()
        assert_that(len(id), is_(equal_to(1)), "expected a single byte id")
        assert_that(id[0], all_of(greater_than(0), less_than(255)))

    def test_reset_eeprom(self):
        """ given an established controller (the test fixture) with an assigned system id
            when a reset with eeprom clear is issued, then the system id is cleared
            indirectly, this tests all the controller/conduit/protocol create/destory due to a reset,
            which closes the conduit to the embedded controller.
        """
        # todo - the system id of 1 byte is specific to the arduino. other devices may manage their IDs differently
        controller_id = self.controller.system_id().read()
        assert_that(controller_id, is_not(equal_to(b'\xFF')), "expected system id to have been assigned")
        self.initialize_id = False
        self.reset(True)                        # restart the controller and erase the eeprom
        controller_id = self.controller.system_id().read()
        assert_that(controller_id, is_(equal_to(b'\xFF')), "expected id to have been reset on erase eeprom")

    def test_create_multiple_profiles(self):
        """ given a new controller,
            when creating the maximum number of profiles, then each profile should have a distinct profile id
            when another profile is created, then an exception is thrown
        """
        current_id = Profile.id_for(self.c.active_and_available_profiles()[0])
        profiles = []
        for x in profile_id_range():
            p = self.c.create_profile()
            profiles.append(p)
            assert_that(p.profile_id, is_(equal_to(x)))
            self.assert_active_available(current_id, range(0,x+1))

        assert_that(calling(self.c.create_profile), raises(FailedOperationError), "expected failre since max profiles "
                                                                                    "are created")
        # assert we can activate each profile
        for x in profile_id_range():
            self.c.activate_profile(profiles[x])
            self.assert_active_available(x, profile_id_range())
            self.c.activate_profile(None)
            self.assert_active_available(-1, profile_id_range())

        for x in profile_id_range():
            self.c.activate_profile(profiles[x])
            p = self.c.delete_profile(profiles[x])
            p = self.c.delete_profile(profiles[x])      # second call succeeds also - deleting is idempotent
            self.assert_active_available(-1, range(x+1,profile_id_range().stop))



    def test_stress_object_creation(self):
        """
        Erases
        :return:
        :rtype:
        """

    def test_delete_profile_preserves_other_profiles(self):
        """ create several profiles, and fetch their contained objects (as a large data block for efficiency)
            delete the profiles from first to last, and verify the contents in other profiles is preserved.
        """


    def test_last_profile_is_open_after_unload(self):
        """ Creates and activates a profile 1 with some objects, then creates a new profile 2.
            Verifies that after creating profile 2, profile 1 is still active.
            Verifies that profile 1 is closed, so that new objects cannot be added to it.
            Finally, after activating profile 2, this profile is open.
        """

    def test_delete_active_profile(self):
        """ creates a profile with some objects
            deletes the profile
            verifies the list of profiles doesn't include this one and that the active profile is -1.
        """

    def test_switch_profiles(self):
        """ create distinct profiles with different objects in each.
            verifies that activating profiles activates the appropriate objects.
        """

    def test_open_profile_not_closed(self):
        """ adds objects to the open profile, and then causes a reset.
            on startup, verifies that the profile is still open. """

    @abstractmethod
    def create_controller(self):
        raise NotImplementedError

    def assert_active_available(self, expected_active, expected_available):
        aa = self.c.active_and_available_profiles()
        active = Profile.id_for(aa[0])
        available = [Profile.id_for(p) for p in aa[1]]
        assert_that(active, is_(equal_to(expected_active)), "active profile")
        assert_that(tuple(available), is_(equal_to(tuple(expected_available))), "available profiles")


if __name__ == '__main__':
    unittest.main()

