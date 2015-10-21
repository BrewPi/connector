from hamcrest import assert_that, is_, equal_to
from connector.v03x.time import ValueProfileState, ValueProfileInterpolation, TimeValuePoint

__author__ = 'mat'

import unittest


class ValueProfileStateTestCase(unittest.TestCase):

    def test_new_instances_equal(self):
        v1 = ValueProfileState()
        v2 = ValueProfileState()
        assert_that(v1, is_(equal_to(v2)))

    def test_new_instance_decoded_equal(self):
        v1 = ValueProfileState()
        enc = v1.encode()
        v2 = ValueProfileState()
        v2.decode(enc)
        assert_that(v1, is_(equal_to(v2)))

    def test_encode_round_trip(self):
        p = ValueProfileState()
        p.current_time_offset = 65320      # 16 bits unsigned
        p.interpolation = ValueProfileInterpolation.amoother
        p.current_step = 3
        p.running = True
        p.steps = [TimeValuePoint(30, 10), TimeValuePoint(
            65535, 12345), TimeValuePoint(20, -20)]

        buf = p.encode()

        p2 = ValueProfileState()
        p2.decode(buf)

        assert_that(p, is_(equal_to(p2)))
