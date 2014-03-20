from collections import OrderedDict

from hamcrest import assert_that, equal_to, is_, not_none

from conduit.base import DefaultConduit
from protocol.test.v03x_test import RWCacheBuffer
from protocol.v02x import BrewpiProtocolV023
import unittest



__author__ = 'mat'

def argument_capture_callback(l):
    def callback(arg):
        l.append(arg)

    return callback


class BrewpiProtocolV023UnitTest(unittest.TestCase):
    def setUp(self):
        self.send = RWCacheBuffer()
        self.receive = RWCacheBuffer()
        self.conduit = DefaultConduit(self.receive.reader, self.send.writer)
        self.protocol = BrewpiProtocolV023(self.conduit)

    def test_read_write_buffer(self):
        buffer = self.receive
        buffer.writer.write(b'abc')
        buffer.writer.flush()
        result = buffer.reader.readline()
        assert_that(result, is_(b'abc'))

    def test_update_values_json_request(self):
        # set the values
        future = self.protocol.update_values_json(OrderedDict([("a", 1), ("b", 2)]))

        # verify stream data was written
        self.assert_request(b'j{"a": 1, "b": 2}\n')
        assert_that(future.response, is_(None), "set values has no response")

    def test_async_response(self):
        # register a callback that simply saves all the arguments passed
        args = list()
        self.protocol.add_unmatched_response_handler(argument_capture_callback(args))

        self.receive.writer.write(b'C{"a": 1, "b": 2}\n')         # fake a received command
        self.receive.writer.flush()
        r = self.protocol.read_response()
        assert_that(r, is_(not_none()), "no response received")
        assert_that(r.value, equal_to({"a": 1, "b": 2}), "expected response from contents in stream")
        assert_that(args[0], is_(r), "expected callback to have been invoked")

    def assert_request(self, expected):
        self.conduit.output.flush()
        line = self.send.reader.readline()
        assert_that(line, equal_to(expected))


if __name__ == '__main__':
    unittest.main()
