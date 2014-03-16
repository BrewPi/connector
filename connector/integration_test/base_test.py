from abc import abstractmethod

__author__ = 'mat'

import unittest


class BaseTestCase(unittest.TestCase):

    def setUp(self):
        """ subclass creates the controller
        """
        self.controller = self.create_controller()
        self.controller.connector.protocol.start_background_thread()
        self.controller.full_erase()

    def tearDown(self):
        self.controller.connector.protocol.stop_background_thread()
        self.controller.connector.disconnect()

    def setup_profile(Self):
        profile = Self.controller.create_profile()
        profile.activate()

    def test_stress_object_creation(self):
        """
        Erases
        :return:
        :rtype:
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


if __name__ == '__main__':
    unittest.main()

