from collections import OrderedDict
from io import BytesIO
from io import BufferedRWPair

from hamcrest import assert_that, equal_to, is_

from conduit.base import DefaultConduit
from protocol.v02x import BrewpiProtocolV023, VersionParser


__author__ = 'mat'

import unittest


__author__ = 'mat'



# todo - use the CircularBuffer class that I wrote after this
class BufferHandle(BufferedRWPair):
    def __init__(self):
        self.buffer = bytearray()
        self.writer = BytesIO(self.buffer)
        self.reader = self.writer
        super().__init__(self.reader, self.writer)

    def make_readable(self):
        self.flush()
        self.reader = BytesIO(self.writer.getvalue())
        super().__init__(self.reader, self.writer)


def argument_capture_callback(l):
    def callback(arg):
        l.append(arg)

    return callback


class BrewpiProtocolV023UnitTest(unittest.TestCase):
    def setUp(self):
        self.send = BufferHandle()
        self.receive = BufferHandle()
        self.conduit = DefaultConduit(self.receive.reader, self.send.reader)
        self.protocol = BrewpiProtocolV023(self.conduit)

    def test_read_write_buffer(self):
        buffer = self.receive
        buffer.write(b'abc')
        buffer.make_readable()
        result = buffer.readline()
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

        # fake a received command
        self.receive.write(b'C{"a": 1, "b": 2}\n')
        self.receive.make_readable()
        r = self.protocol.read_response()

        assert_that(r.value, equal_to({"a": 1, "b": 2}), "expected response from contents in stream")
        assert_that(args[0], is_(r), "expected callback to have been invoked")


    def assert_request(self, expected):
        self.conduit.output.flush()
        line = self.conduit.output.writer.getvalue()
        assert_that(line, equal_to(expected))


if __name__ == '__main__':
    unittest.main()
