import io
from hamcrest import assert_that, calling, raises, is_, instance_of

from conduit.base import DefaultConduit
from connector.base import ConnectorError, UnknownProtocolError
from protocol.factory import determine_protocol
from protocol.v02x import BrewpiProtocolV023
from protocol.v03x import HexToBinaryInputStream, BrewpiProtocolV030

__author__ = 'mat'

import unittest


def build_conduit(data):
    return DefaultConduit(io.BytesIO(data), io.BytesIO())


class FactoryTestCase(unittest.TestCase):

    def test_no_input_raises_unknown_protocol(self):
        c = build_conduit(b'')
        assert_that(calling(determine_protocol).with_args(c), raises(UnknownProtocolError))


    def test_create_v020(self):
        c = build_conduit(b'N:0.2.0\n')
        assert_that(calling(determine_protocol).with_args(c), raises(UnknownProtocolError))

    def test_create_v023(self):
        c = build_conduit(b'N:0.2.3\n')
        p = determine_protocol(c)
        assert_that(p, is_(instance_of(BrewpiProtocolV023)))
        assert_that(p._conduit, is_(c))

    def test_create_v030(self):
        c = build_conduit(b'["v":"0.3.0"]\n')
        p = determine_protocol(c)
        assert_that(p, is_(instance_of(BrewpiProtocolV030)))
        assert_that(p._conduit.input, is_(instance_of(HexToBinaryInputStream)))


if __name__ == '__main__':
    unittest.main()
