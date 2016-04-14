import io
import unittest

from hamcrest import assert_that, calling, raises, is_, instance_of

from brewpi.protocol.factory import all_sniffers
from brewpi.protocol.v02x import ControllerProtocolV023
from controlbox.conduit.base import DefaultConduit
from controlbox.connector.base import UnknownProtocolError
from controlbox.protocol.controlbox import HexToBinaryInputStream, ControllerProtocolV030
from controlbox.protocol.io import determine_line_protocol


def build_conduit(data):
    return DefaultConduit(io.BytesIO(data), io.BytesIO())


class FactoryTestCase(unittest.TestCase):

    def test_no_input_raises_unknown_protocol(self):
        c = build_conduit(b'')
        assert_that(calling(determine_line_protocol).with_args(c, all_sniffers),
                    raises(UnknownProtocolError))

    def test_create_v020(self):
        c = build_conduit(b'N:0.2.0\n')
        assert_that(calling(determine_line_protocol).with_args(c, all_sniffers),
                    raises(UnknownProtocolError))

    def test_create_v023(self):
        c = build_conduit(b'N:0.2.3\n')
        p = determine_line_protocol(c, all_sniffers)
        assert_that(p, is_(instance_of(ControllerProtocolV023)))
        assert_that(p._conduit, is_(c))

    def test_create_v030(self):
        c = build_conduit(b'["v":"0.3.0"]\n')
        p = determine_line_protocol(c, all_sniffers)
        assert_that(p, is_(instance_of(ControllerProtocolV030)))
        assert_that(p._conduit.input, is_(instance_of(HexToBinaryInputStream)))


if __name__ == '__main__':
    unittest.main()
