from hamcrest import assert_that, equal_to, is_
from connector.v03x.controller import Controller, Container, RootContainer, SystemProfile

__author__ = 'mat'

import unittest


class ControllerTest(unittest.TestCase):
    """ unit test for the controller
    """

    def test_containers_equal(self):
        c = Controller()
        p = SystemProfile(c, 1)
        r = RootContainer(p)
        c1 = Container(c, r, 0)
        c2 = Container(c, r, 0)
        assert_that(c1, is_(equal_to(c2)))
        assert_that(c2, is_(equal_to(c1)))


if __name__ == '__main__':
    unittest.main()
