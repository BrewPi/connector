from unittest.mock import Mock, MagicMock
from hamcrest import assert_that, is_, equal_to
from connector.v03x.controller import fetch_dict, ForwardingDecoder, ValueDecoder, ValueEncoder, ForwardingEncoder, \
    EncoderDecoderDefinition, ControllerLoop, ControllerLoopState, ControllerLoopContainer, SystemProfile, \
    DynamicContainer, BaseController

__author__ = 'mat'

import unittest


class FetchDictTestCase(unittest.TestCase):
    def test_fetch_not_exist(self):
        d = dict()
        result = fetch_dict(d, 123, lambda x: x+1)
        assert_that(result, is_(124))

    def test_fetch_exist(self):
        d = dict()
        d[123] = "abc"
        result = fetch_dict(d, 123, lambda x: x/0)
        assert_that(result, is_("abc"))


class ForwardDecoderTestCase(unittest.TestCase):
    def test_forward_and_return_encoded_len(self):
        decoder = ValueDecoder()
        decoder.encoded_len = MagicMock(return_value=3)
        sut = ForwardingDecoder(decoder)
        assert_that(sut.encoded_len(),is_(3))
        decoder.encoded_len.assert_called_once_with()

    def test_forward_and_return_decoded_value(self):
        decoder = ValueDecoder()
        decoder.decode = MagicMock(return_value=4)
        sut = ForwardingDecoder(decoder)
        assert_that(sut.decode(b'4'), is_(4))
        decoder.decode.assert_called_once_with(b'4')


class ForwardEncoderTestCase(unittest.TestCase):
    def test_forward_and_return_encoded_len(self):
        encoder = ValueEncoder()
        encoder.encoded_len = MagicMock(return_value=3)
        sut = ForwardingEncoder(encoder)
        assert_that(sut.encoded_len(),is_(3))
        encoder.encoded_len.assert_called_once_with()

    def test_forward_and_return_encoded_value(self):
        encoder = ValueEncoder()
        encoder.encode = MagicMock(return_value=b'123')
        sut = ForwardingEncoder(encoder)
        assert_that(sut.encode(123), is_(b'123'))
        encoder.encode.assert_called_once_with(123)

    def test_assigning_instance_separate_from_class(self):
        sut = ForwardingEncoder()
        sut.encode = MagicMock()
        assert_that(ForwardingEncoder.encoder, is_(None))

class EncoderDecoderDefinitionTest(unittest.TestCase):
    def test_encode_definition(self):
        defn = EncoderDecoderDefinition()


class ControllerLoopStateTest(unittest.TestCase):
    def test_value_to_log_period_dictionary(self):
        p = ControllerLoopState().log_periods()
        assert_that(p.get(0), is_(0))
        assert_that(p.get(1), is_(1))
        assert_that(p.get(2), is_(2))
        assert_that(p.get(3), is_(4))
        assert_that(p.get(4), is_(8))
        assert_that(p.get(5), is_(16))
        assert_that(p.get(6), is_(32))
        assert_that(p.get(7), is_(64))

    def test_encoded_len(self):
        assert_that(ControllerLoopState().encoded_len(), is_(3))

    def test_encode_loop_state_empty(self):
        self.assert_encode(ControllerLoopState(), b'\x00\x00\x00', b'\x00\x00\x00')

    def test_encode_loop_state_period(self):
        self.assert_encode(ControllerLoopState(None, None, 520), b'\x00\x08\x02', b'\x00\xFF\xFF')

    def test_encode_loop_state_enabled(self):
        self.assert_encode(ControllerLoopState(True), b'\x08\x00\x00', b'\x08\x00\x00')

    def test_encode_loop_state_disabled(self):
        self.assert_encode(ControllerLoopState(False), b'\x00\x00\x00', b'\x08\x00\x00')

    def test_encode_loop_state_log_period(self):
        self.assert_encode(ControllerLoopState(None, 3), b'\x03\x00\x00', b'\x07\x00\x00')

    def test_encode_loop_state_enabled_log_period(self):
        self.assert_encode(ControllerLoopState(True, 3), b'\x0B\x00\x00', b'\x0F\x00\x00')

    def test_encode_loop_state_enabled_log_period_period(self):
        self.assert_encode(ControllerLoopState(True, 5, 521), b'\x0D\x09\x02', b'\x0F\xFF\xFF')

    def test_decode_state(self):
        assert_that(ControllerLoopState().decode(b'\x0D\x09\x02'), is_(equal_to(ControllerLoopState(True, 5, 521))))

    def assert_encode(self, state, value, mask):
        len = state.encoded_len()
        actual_value, actual_mask = state.encode_mask(bytearray(len), bytearray(len))
        assert_that(actual_value, is_(equal_to(value)))
        assert_that(actual_mask, is_(equal_to(mask)))


class ControllerLoopTest(unittest.TestCase):
    def test_encoded_len(self):
        sut = ControllerLoop(None, None, 1)
        len = sut.encoded_len()
        assert_that(len, is_(3))

    def test_encode_decode(self):
        sut = ControllerLoop(None, None, 1)
        value = ControllerLoopState(True, 10, 5)
        buf, mask = sut.encode_masked(value)



class ControllerLoopContainerTest(unittest.TestCase):
    def setUp(self):
        c = None
        p = SystemProfile(c, 1)
        self.sut = ControllerLoopContainer(p)
        self.c = c

    def test_adding_new_component_adds_config(self):
        o = DynamicContainer(self.c, None, 1)
        self.sut.notify_added(o)
        assert_that(self.sut.configurations[1], is_(equal_to(ControllerLoop(self.c, self.sut.config_container, 1))))

    def test_removing_component_removes_config(self):
        o = DynamicContainer(self.c, None, 1)
        self.sut.notify_added(o)
        assert_that(self.sut.configurations.get(1, None), is_(equal_to(ControllerLoop(self.c, self.sut.config_container, 1))))
        self.sut.notify_removed(o)
        assert_that(self.sut.configurations.get(1, None), is_(None))
