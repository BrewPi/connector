from abc import abstractmethod, ABCMeta
from hamcrest import assert_that, equal_to, is_, greater_than, less_than, calling, raises, is_not, all_of, any_of
from connector import controller_id
from connector.v03x import BaseController, FailedOperationError, Profile, ContainedObject, ReadableObject

__author__ = 'mat'

import unittest

no_stress_tests = True

def profile_id_range():
    return range(0,4)

class BaseControllerTestHelper(metaclass=ABCMeta):
    def initialize_controller(self):
        self.controller = self.create_controller()
        self.create_connection()

    def setUp(self):
        """ subclass creates the controller. Ensures the controller has no profiles defined."""
        self.initialize_controller()
        self.test_has_assigned_id()
        self.controller.full_erase()
        act = self.c.active_and_available_profiles()
        self.assert_active_available(-1, []) # verify that profiles have been cleared
        assert_that(act[0], is_(None), "no profile should be loaded by default")
        assert_that(len(act[1]), is_(0), "no profiles created by default")

    def id_service(self):
        return controller_id.simple_id_service

    def create_connection(self):
        self.c.connector.connect()
        self.protocol = self.controller.connector.protocol    # so we can access the protocol when the conduit is disconnected
        self.protocol.start_background_thread()

    def discard_connection(self):
        self.c.connector.disconnect()
        self.protocol.stop_background_thread()

    def tearDown(self):
        self.controller.reset(True)
        self.discard_connection()

    def reset(self, erase_eeprom=False):
        """ allows for a controller reset mid-test """
        self.controller.reset(erase_eeprom)
        self.discard_connection()
        self.create_connection()

    def setup_profile(self) -> Profile:
        """ create a profile and activate it. Verifies that it is active. """
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

    @unittest.skip
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

    @unittest.skipIf(no_stress_tests, "stress tests disabled")
    def test_stress_object_creation(self):
        count = self.fill_profile()
        assert_that(count, is_(greater_than(63)))
        for x in range(0,3):
            self.c.full_erase()
            count2 = self.fill_profile()
            assert_that(count2, is_(any_of(greater_than(count), equal_to(count))))

    def fill_profile(self):
        """ creates as many objects as possible in the current profile. """
        self.setup_profile()
        count = 0
        while True:
            try:
                self.create_object()
                count += 1
            except FailedOperationError as e:
                break
        return count

    @unittest.skip
    def test_delete_profile_preserves_other_profiles(self):
        """ create several profiles, and fetch their contained objects (as a large data block for efficiency)
            delete the profiles from first to last, and verify the contents in other profiles is preserved.
        """

    @unittest.skip
    def test_last_profile_is_open_after_unload(self):
        """ Creates and activates a profile 1 with some objects, then creates a new profile 2.
            Verifies that after creating profile 2, profile 1 is still active.
            Verifies that profile 1 is closed, so that new objects cannot be added to it.
            Finally, after activating profile 2, this profile is open.
        """
        p1 = self.setup_profile()
        o1a = self.create_object()
        o2a = self.create_object()
        p2 = self.c.create_profile()
        assert_that(p1.is_active, is_(True), "expected profile to still be active")
        assert_that(calling(self.create_object), (raises(FailedOperationError)), "profile should still be closed")
        p2.activate()
        assert_that(calling(self.create_object), is_not(raises(FailedOperationError)), "profile p2 should be open")
        o2 = self.create_object()
        assert_that(o2.id_chain, is_(equal_to(1,))) # second object in this profile
        p1.delete()
        assert_that(p2.is_active, is_(True), "expected profile 2 to still be active")
        assert_that(calling(o2.read), is_not(raises(FailedOperationError)), "o2 should be readable")
        p2.delete()

    def test_delete_active_profile(self):
        """ creates a profile with some objects
            deletes the profile
            verifies the list of profiles doesn't include this one and that the active profile is -1.
        """
        p = self.setup_profile()
        self.create_object()
        p.delete()
        self.assert_active_available(-1, [])

    @unittest.skip
    def test_switch_profiles(self):
        """ create distinct profiles with different objects in each.
            verifies that activating profiles activates the appropriate objects.
        """

    def test_open_profile_not_closed(self):
        """ adds objects to the open profile, and then causes a reset.
            on startup, verifies that the profile is still open, by creating more objects. """
        p = self.setup_profile()
        #o0 = self.create_object()
        self.reset()
        # after reset (when the connection is broken) all existing objects should be revalidated
        # against the controller.
        self.assert_active_available(p.profile_id, [p.profile_id])
        assert_that(p.is_active, is_(equal_to(True)), "profile should be active after reset")
        assert_that(calling(self.create_object), is_not(raises(FailedOperationError)), "profile should be open after reset")
        o2 = self.create_object()
        #assert_that(o2.id_chain, is_(equal_to((o0.slot+2,))))

    def test_delete_active_profile(self):
        p = self.setup_profile()
        p.delete()
        self.assert_active_available(-1, [])
        self.reset()
        self.assert_active_available(-1, [])

    def test_deleted_slots_are_reused(self):
        """ adds objects to the open profile, and then causes a reset.
            on startup, verifies that the profile is still open, by creating more objects. """
        p = self.setup_profile()
        o0 = self.create_object()
        o1 = self.create_object()
        o2 = self.create_object()
        slot = o1.slot
        o1.delete()
        o4 = self.create_object()
        assert_that(o4.slot, is_(equal_to(slot)), "expected new object to use same slot as deleted object")

    def test_reset_preserves_inactive_profile(self):
        self.c.activate_profile(None)
        self.assert_active_available(-1, []) # verify that profiles have been cleared
        self.reset()                         # do the reset
        self.assert_active_available(-1, []) # tests that the connection comes back up

    def test_reset_preserves_active_profile(self):
        self.assert_active_available(-1, []) # verify that profiles have been cleared
        p = self.setup_profile()
        self.assert_active_available(p.profile_id, [p.profile_id]) # tests that the connection comes back up
        self.reset()                         # do the reset
        self.assert_active_available(p.profile_id, [p.profile_id]) # tests that the connection comes back up


    def create_object(self)->ReadableObject:
        """ create some arbitrary object. """
        return self.c.create_object_current_ticks(self.c.root_container)

    @abstractmethod
    def create_controller(self):
        raise NotImplementedError

    def assert_active_available(self, expected_active:int, expected_available:list):
        aa = self.c.active_and_available_profiles()
        active = Profile.id_for(aa[0])
        available = [Profile.id_for(p) for p in aa[1]]
        assert_that(active, is_(equal_to(expected_active)), "active profile")
        assert_that(tuple(available), is_(equal_to(tuple(expected_available))), "available profiles")



if __name__ == '__main__':
    unittest.main()

