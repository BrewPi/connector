import sys
from time import sleep
from hamcrest import assert_that, equal_to, is_, greater_than, less_than, calling, raises, is_not, all_of, any_of, \
    has_length, empty
from connector import id_service
from connector.v03x.controller import *
from connector.v03x.objects import PersistentValue, PersistChangeValue, DynamicContainer, MixinController
from connector.v03x.time import CurrentTicks
from test.config import apply_module
from abc import abstractmethod, ABCMeta

__author__ = 'mat'

import unittest

apply_module(sys.modules[__name__])

stress_tests_enabled = None
broken_tests_enabled = None


def profile_id_range():
    return range(0, 4)


class TestController(MixinController):
    pass


class ControllerObjectTestCase(unittest.TestCase):

    def setUp(self):
        self.connector = None
        self.controller = TestController(self.connector)


class RootContainerTestCase(ControllerObjectTestCase):

    def create_root(self):
        p = SystemProfile(self.controller, 1)
        r = RootContainer(p)
        return r

    def test_id_chain_for_root_is_empty(self):
        r = self.create_root()
        assert_that(r.id_chain, is_(equal_to(tuple())))

    def test_id_chain_for_slot(self):
        r = self.create_root()
        assert_that(r.id_chain_for(10), is_(equal_to(tuple([10]))))


class ContainerObjectTestCase(ControllerObjectTestCase):

    def test_id_chain_for_nested_container(self):
        p = SystemProfile(self.controller, 1)
        r = RootContainer(p)
        c1 = Container(self.controller, r, 5)
        assert_that(c1.id_chain, is_(equal_to((5,))))

    def test_id_chain_for_nested_slot(self):
        p = SystemProfile(self.controller, 1)
        r = RootContainer(p)
        c1 = Container(self.controller, r, 5)
        assert_that(c1.id_chain_for(10), is_(equal_to((5, 10))))


class BaseControllerTestHelper(unittest.TestCase):
    """ Setup connects to the controller and verifies it has been assigned an ID.
        Erases all existing state so the test starts with a completely blank state.
    """
    __test__ = False

    connector = None
    controller = None
    initialize_id = True

    def initialize_controller(self):
        self.connector = self.create_connector()
        self.controller = self.create_controller()
        self.create_connection()

    def setUp(self):
        """ subclass creates the controller. Ensures the controller has no profiles defined."""
        self.initialize_id = True
        success = False
        try:
            self.initialize_controller()
            self.assert_has_assigned_id()
            self.controller.full_erase()
            act = self.c.active_and_available_profiles()
            assert_that(act[0], is_(None),
                        "no profile should be loaded by default")
            assert_that(len(act[1]), is_(0), "no profiles created by default")
            success = True
        finally:
            if not success and self.connector:
                self.connector.disconnect()

    def assert_has_assigned_id(self):
        assigned_id = self.c.system_id().read()
        assert_that(len(assigned_id), is_(equal_to(1)),
                    "expected a single byte id")
        assert_that(assigned_id[0], all_of(greater_than(0), less_than(255)))

    @abstractmethod
    def create_controller(self):
        raise NotImplementedError

    @abstractmethod
    def create_connector(self):
        raise NotImplementedError

    def assert_active_available(self, expected_active: int, expected_available):
        aa = self.c.active_and_available_profiles()
        active = SystemProfile.id_for(aa[0])
        available = [SystemProfile.id_for(p) for p in aa[1]]
        assert_that(active, is_(equal_to(expected_active)), "active profile")
        assert_that(tuple(available), is_(
            equal_to(tuple(expected_available))), "available profiles")

    def assign_id(self):
        return id_service.simple_id_service

    def create_connection(self, load_profile=False):
        # todo - this is generic and a basic requirement of all connected
        # devices that the ID is assigned.
        self.connector.connect()
        # so we can access the protocol when the conduit is disconnected
        self.protocol = self.connector.protocol
        self.protocol.start_background_thread()
        if self.initialize_id:
            self.controller.initialize(self.assign_id(), load_profile)

    def discard_connection(self):
        self.c.disconnect()
        self.protocol.stop_background_thread()

    def tearDown(self):
        self.discard_connection()

    def reset(self, erase_eeprom=False):
        """ allows for a controller reset mid-test """
        # todo - the controller should determine the appropriate reset required
        # desktop/leonardo - do a full reset
        # mega/uno - do not, since serial connection does a reset
        self.controller.reset(erase_eeprom, False)
        self.discard_connection()
        self.create_connection(load_profile=True)

    def setup_profile(self) -> SystemProfile:
        """ create a profile and activate it. Verifies that it is active. """
        profile = self.c.create_profile()
        profile.activate()
        assert_that(profile.is_active, is_(True))
        return profile

    @property
    def c(self) -> MixinController:  # some type hinting for the IDE
        return self.controller


class GeneralControllerTests(BaseControllerTestHelper):
    """ The original test suite before they were factored out in to separate test classes """

    def test_has_assigned_id(self):
        self.assert_has_assigned_id()

    def test_reset_eeprom(self):
        """ given an established controller (the test fixture) with an assigned system id
            when a reset with eeprom clear is issued, then the system id is cleared
            indirectly, this tests all the controller/conduit/protocol create/destory due to a reset,
            which closes the conduit to the embedded controller.
        """
        # todo - the system id of 1 byte is specific to the arduino. other
        # devices may manage their IDs differently
        controller_id = self.controller.system_id().read()
        assert_that(controller_id, is_not(equal_to(b'\xFF')),
                    "expected system id to have been assigned")
        self.initialize_id = False
        self.reset(True)  # restart the controller and erase the eeprom
        controller_id = self.controller.system_id().read()
        assert_that(controller_id, is_(equal_to(b'\xFF')),
                    "expected id to have been reset on erase eeprom")

    def test_create_max_profiles(self):
        """ creates many profiles and verifies they have distinct ids:
                given a new controller,
                when creating the maximum number of profiles, then each profile should have a distinct profile id
                when another profile is created, then an exception is thrown
        """
        current_id = SystemProfile.id_for(
            self.c.active_and_available_profiles()[0])
        profiles = []
        for x in profile_id_range():
            p = self.c.create_profile()
            profiles.append(p)
            assert_that(p.profile_id, is_(equal_to(x)))
            self.assert_active_available(current_id, range(0, x + 1))
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
            # second call succeeds also - deleting is idempotent
            p = self.c.delete_profile(profiles[x])
            self.assert_active_available(-1,
                                         range(x + 1, profile_id_range().stop))

    @unittest.skipUnless(stress_tests_enabled, "stress tests disabled")
    def test_stress_object_creation(self):
        count = self.fill_profile()
        assert_that(count, is_(greater_than(63)))
        for x in range(0, 3):
            self.c.full_erase()
            count2 = self.fill_profile()
            assert_that(count2, is_(
                any_of(greater_than(count), equal_to(count))))

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

    @unittest.skipUnless(stress_tests_enabled, "stress tests disabled")
    def test_deactivating_profile_frees_space(self):
        """ fills up eeprom space by successvely creating and deleting objects until no more objects can be created.
            creates a new profile, and verifies that additional objects can be added to that.
        """
        p = self.setup_profile()
        error = None
        for x in range(0, 10000):  # limit the number of attempts
            try:
                obj = self.c.create_current_ticks(self.c.root_container)
            except FailedOperationError as e:
                error = e
                break
            obj.delete()  # if this throws an exception the test fails

        assert_that(tuple(self.c.list_objects(p)), is_(empty()))
        assert_that(error, is_not(None), "expected an exception")
        p.deactivate()
        p.activate()

        # this should succeed now, since the store has been compacted
        self.c.create_current_ticks(self.c.root_container)

    @unittest.skip
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
        p1 = self.setup_profile()
        first_slot = 1
        o1a = self.create_object()
        o2a = self.create_object()
        p2 = self.c.create_profile()
        assert_that(p1.is_active, is_(True),
                    "expected profile to still be active")
        assert_that(calling(self.create_object), (raises(
            FailedOperationError)), "profile should still be closed")
        p2.activate()
        assert_that(calling(self.create_object), is_not(
            raises(FailedOperationError)), "profile p2 should be open")
        o2 = self.create_object()
        # second object in this profile
        assert_that(o2.id_chain, is_(equal_to((first_slot + 1,))))
        p1.delete()
        assert_that(p2.is_active, is_(True),
                    "expected profile 2 to still be active")
        assert_that(calling(o2.read), is_not(
            raises(FailedOperationError)), "o2 should be readable")
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

    def test_switch_profiles(self):
        """ create distinct profiles with different objects in each.
            verifies that activating profiles activates the appropriate objects.
        """
        c = self.c
        p1 = self.setup_profile()
        o10 = c.create_object(CurrentTicks)
        b1 = b'\x09\xA0\xFF'
        o11 = c.create_object(PersistentValue, b1)
        p2 = self.setup_profile()
        b2 = b'\x19\xA1\xFE\x00\x01'
        # reversed order so they are in different slots
        o20 = c.create_object(PersistentValue, b2)
        c.create_object(CurrentTicks)
        self.reset()
        # verify profiles can be listed
        first_slot = 1
        expected1 = (c.ref(CurrentTicks, None, (first_slot,)),
                     c.ref(PersistentValue, b1, (first_slot + 1,)))
        expected2 = (c.ref(PersistentValue, b2, (first_slot,)),
                     c.ref(CurrentTicks, None, (first_slot + 1,)))
        assert_that(tuple(c.list_objects(p2)), is_(equal_to(expected2)))
        assert_that(tuple(c.list_objects(p1)), is_(equal_to(expected1)))
        # verify values can be read - initially in profile 2
        assert_that(
            p2.is_active, "expected p2 to be the active profile after reset")
        assert_that(c.read_value(o20), is_(b2),
                    "value of persistent object in 2nd profile")
        p1.activate()
        assert_that(c.read_value(o11), is_(b1),
                    "value of persistent object in 1st profile")
        o10 = p1.refresh(o10)
        o10.delete()
        assert_that(tuple(c.list_objects(p1)), is_(equal_to(tuple([c.ref(PersistentValue, b1, (first_slot + 1,))]))),
                    "should remove deleted object")

    def test_open_profile_not_closed(self):
        """ adds objects to the open profile, and then causes a reset.
            on startup, verifies that the profile is still open, by creating more objects. """
        p = self.setup_profile()
        #o0 = self.create_object()
        self.reset()
        # after reset (when the connection is broken) all existing objects should be revalidated
        # against the controller.
        self.assert_active_available(p.profile_id, [p.profile_id])
        assert_that(p.is_active, is_(equal_to(True)),
                    "profile should be active after reset")
        assert_that(calling(self.create_object), is_not(raises(FailedOperationError)),
                    "profile should be open after reset")
        o2 = self.create_object()
        #assert_that(o2.id_chain, is_(equal_to((o0.slot+2,))))

    def test_delete_active_profile_survives_reset(self):
        p = self.setup_profile()
        self.reset()
        self.assert_active_available(0, [0])
        p.delete()
        self.assert_active_available(-1, [])
        self.reset()
        self.assert_active_available(-1, [])

    def test_reset_preserves_inactive_profile(self):
        self.c.activate_profile(None)
        # verify that profiles have been cleared
        self.assert_active_available(-1, [])
        self.reset()  # do the reset
        # tests that the connection comes back up
        self.assert_active_available(-1, [])

    def test_reset_preserves_active_profile(self):
        # verify that profiles have been cleared
        self.assert_active_available(-1, [])
        p = self.setup_profile()
        # tests that the connection comes back up
        self.assert_active_available(p.profile_id, [p.profile_id])
        self.reset()  # do the reset
        # tests that the connection comes back up
        self.assert_active_available(p.profile_id, [p.profile_id])

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
        assert_that(o4.slot, is_(equal_to(slot)),
                    "expected new object to use same slot as deleted object")

    def test_list_objects_after_delete(self):
        p = self.setup_profile()
        assert_that(tuple(self.c.list_objects(p)), has_length(0),
                    "expected no objects in new profile")
        o1 = self.c.create_object(PersistentValue, b'\x00')
        o2 = self.c.create_object(PersistentValue, b'\x01')
        assert_that(tuple(self.c.list_objects(p)), has_length(2),
                    "expected 2 objects in profile")
        o1.delete()
        assert_that(tuple(self.c.list_objects(p)), has_length(1),
                    "expected 1 object in profile")
        o3 = self.c.create_object(PersistentValue, b'\x02')
        assert_that(tuple(self.c.list_objects(p)), has_length(2),
                    "expected 2 objects in profile")

    @unittest.skipUnless(stress_tests_enabled, "stress tests disabled")
    def test_dynamic_container_stress(self):
        self.setup_profile()
        container = self.c.create_dynamic_container(self.c.root_container)
        containers = []
        for x in range(0, 127):
            try:
                containers += [self.c.create_dynamic_container(container)]
            except Exception as e:
                raise AssertionError(
                    "unable to create container %d" % x) from e

        assert_that(containers[0].slot, is_(0))
        # 126 is the highest container ID
        assert_that(containers[-1].slot, is_(126))

        assert_that(calling(self.c.create_dynamic_container).with_args(container), raises(FailedOperationError),
                    "expected container to be full")
        containers[20].delete()
        assert_that(calling(self.c.create_dynamic_container).with_args(container), is_not(raises(FailedOperationError)),
                    "expected container to have one free slot")
        assert_that(calling(self.c.create_dynamic_container).with_args(container), raises(FailedOperationError),
                    "expected container to be full")

    def test_dynamic_container_create_destroy(self):
        self.setup_profile()
        container = self.c.create_dynamic_container(self.c.root_container)
        container2 = self.c.create_dynamic_container(container)
        container3 = self.c.create_dynamic_container(container2)

        container3.delete()
        container2.delete()
        container.delete()

    def test_dynamic_container_allocate_slot_dynamically(self):
        """ the dynamic container initially has a size of zero, and should be expanded by calling next_slot,
            before adding objects. This test verifies that attempting to create an object without calling next_slot
            fails.
        """
        self.setup_profile()
        container = self.c.create_dynamic_container(self.c.root_container)
        ticks = self.c.create_current_ticks(container, 20)
        ticks.read()

    def test_create_object_with_inactive_profile_fails(self):
        p = self.setup_profile()
        p.deactivate()
        assert_that(calling(self.c.create_dynamic_container),
                    raises(FailedOperationError),
                    "expected container creation to fail with no active profile")

    def test_create_object_in_closed_profile_fails(self):
        p = self.setup_profile()
        p2 = self.setup_profile()
        p3 = self.setup_profile()
        # todo - this used to throw a FailedOperationError with only 2 profiles (no p3 above)
        # but after switching to the ControlLoopContainer p2 remained as an open profile.
        # and the second create dynamic container create succeeded (since p2
        # was now considered an open profile.)

        p.activate()
        assert_that(calling(self.c.create_dynamic_container).with_args(self.c.root_container),
                    raises(FailedOperationError),
                    "expected container creation to fail with closed profile")
        p2.activate()
        assert_that(calling(self.c.create_dynamic_container).with_args(self.c.root_container),
                    raises(FailedOperationError),
                    "expected creation to fail in closed profile")

        self.reset()
        assert_that(calling(self.c.create_dynamic_container).with_args(self.c.root_container),
                    raises(FailedOperationError),
                    "expected creation to fail in closed profile")

    def test_object_available_after_reset(self):
        self.setup_profile()
        host = self.c.root_container
        current_ticks = self.c.create_current_ticks(host)
        ticks = current_ticks.read()  # don't care what the value is just that we can read it
        self.reset()
        # technically the current_ticks proxy should be re-evaluated after reset, and read from the controller (list objects)
        # but here, we rely on the id_chain still being valid
        ticks = current_ticks.read()  # don't care what the value is just that we can read it

    def test_list_objects(self):
        c = self.c
        p = self.setup_profile()
        container = c.create_object(DynamicContainer)
        c.create_object(CurrentTicks, None, container)
        refs = tuple(c.list_objects(p))
        expected = (c.ref(DynamicContainer, None, (1,)),
                    c.ref(CurrentTicks, None, (1, 0)))
        for r, e in zip(refs, expected):
            assert_that(r, is_(equal_to(e)))
        assert_that(tuple(refs), is_(equal_to(expected)))

    @unittest.skipUnless(broken_tests_enabled, "broken test")
    def test_persistent_long_value(self):
        self._persist_value(90)

    def test_persistent_short_value(self):
        self._persist_value(10)

    def _persist_value(self, size):
        p = self.setup_profile()
        b = bytes([x for x in range(10, 10 + size)])
        persist = self.c.create_object(PersistentValue, b)
        assert_that(persist.read(), is_(equal_to(b)),
                    "expected initial read value to match initial create value")
        self.reset()
        assert_that(persist.read(), is_(equal_to(b)),
                    "Expected read value to be initial create value after reset")
        b2 = bytes([x for x in range(50, 50 + size)])
        persist.write(b2)
        self.reset()
        assert_that(persist.read(), is_(equal_to(b2)),
                    "Expected read value to be last written value after reset")

    def test_multiple_objects_to_same_slot(self):
        p = self.setup_profile()
        c = self.c
        slot = 1
        o1 = c.create_object(CurrentTicks, None, None, slot)
        o2 = c.create_object(CurrentTicks, None, None, slot)
        o3 = c.create_object(CurrentTicks, None, None, slot)
        o4 = c.create_object(CurrentTicks, None, None, slot + 1)
        result = tuple(self.c.list_objects(p))
        assert_that(result, has_length(
            2), "expected two object definitions at slot 0 and slot 1")
        expected = (c.ref(CurrentTicks, None, (slot,)),
                    c.ref(CurrentTicks, None, (slot + 1,)))
        assert_that(result, is_(equal_to(expected)))

    @unittest.skipUnless(stress_tests_enabled, "stress tests disabled")
    def test_many_persistent_values(self):
        p = self.setup_profile()
        [self.c.create_object(PersistentValue, bytes(240))
         for x in range(0, 4)]
        assert_that(calling(self.c.create_object).with_args(PersistentValue, bytes(240)), raises(FailedOperationError),
                    "Expected last allocation to fail due to insufficient eeprom space")

    def create_object(self) -> CurrentTicks:
        """ create some arbitrary object. """
        return self.c.create_current_ticks(self.c.root_container)


class ObjectTestHelper(BaseControllerTestHelper):
    """ Base class for tests that are more focus on testing objects in profiles. The setup creates a default profile."""

    def setUp(self):
        super().setUp()
        self.setup_profile()
