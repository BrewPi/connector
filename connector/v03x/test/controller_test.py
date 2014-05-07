from unittest.mock import Mock, MagicMock
from hamcrest import assert_that, is_
from connector.v03x.controller import fetch_dict, ForwardingDecoder, ValueDecoder, ValueEncoder, ForwardingEncoder, \
    EncoderDecoderDefinition

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
