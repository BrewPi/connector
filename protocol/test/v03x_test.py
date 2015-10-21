from collections import deque
import io
from io import BufferedReader, BufferedWriter, BytesIO

from hamcrest import assert_that, is_, equal_to, raises, calling

from conduit.base import DefaultConduit
from protocol.v03x import HexToBinaryInputStream, ChunkedHexTextInputStream, BinaryToHexOutputStream, ControllerProtocolV030, \
    build_chunked_hexencoded_conduit


__author__ = 'mat'

import unittest


class DequeStream(io.BufferedIOBase):

    def __init__(self, q: deque):
        super().__init__()
        self.q = q

    def close(self):
        self.q = None
        super().close()


class DequeReader(DequeStream):

    def readable(self):
        return True

    def read(self, count=-1):
        self._checkClosed()
        if not count or not self.q:
            return bytes()
        return bytes([self.q.popleft()])


class DequeWriter(DequeStream):

    def writable(self):
        return True

    def write(self, buf):
        self._checkClosed()
        for x in buf:
            self.q.append(x)
        return len(buf)


class RWCacheBuffer():
    """ simple implementation of a read and writable buffer. For single-threaded code in test.
        Use the reader and writer attributes to access a reader and writer - the reader reads what has been put by the writer.
    """

    def __init__(self):
        self.q = deque()
        self.reader = BufferedReader(DequeReader(self.q))
        self.writer = BufferedWriter(DequeWriter(self.q))

    def close(self):
        self.reader.close()
        self.writer.close()


def h2bstream(content):
    base = io.BytesIO(content.encode("utf-8"))
    base = BufferedReader(base)
    result = HexToBinaryInputStream(base)
    return result


class HexToBinaryStreamTestCase(unittest.TestCase):

    def test_read_from_hex_stream(self):
        hex = h2bstream("FF00")
        assert_that(hex.has_next(), is_(True), "stream should have more data")
        assert_that(hex.peek(1), is_(equal_to(bytes([0xFF]))))
        assert_that(hex.read(1), is_(equal_to(bytes([0xFF]))))
        assert_that(hex.has_next(), is_(True), "stream should have more data")
        assert_that(hex.peek(1), is_(equal_to(bytes([0x00]))))
        assert_that(hex.read(1), is_(equal_to(bytes([0x00]))))
        assert_that(hex.has_next(), is_(False),
                    "stream should have no more data")
        assert_that(hex.peek(1), is_(equal_to(bytes())))
        assert_that(hex.read(1), is_(equal_to(bytes())))

    def test_flags(self):
        s = h2bstream("")
        assert_that(s.writable(), is_(False))
        assert_that(s.readable(), is_(True))


def collect_stream(stream):
    collect = bytearray()
    d = stream.read()
    while d:
        collect += d
        d = stream.read()
    return bytes(collect)


class ChunkedHexTextInputStreamTestCase(unittest.TestCase):

    def test_zero_length_read_returns_empty_array(self):
        base = BufferedReader(io.BytesIO(b"20 00 [[12] comment] AF cd "))
        text = ChunkedHexTextInputStream(base)
        assert_that(text.peek(1), is_(equal_to(b'2')))
        assert_that(text.read(0), is_(equal_to(bytes())))

    def test_example1(self):
        assert_that(self.stream_read(
            b"20 00 [[12] comment] AF cd "), equal_to(b"2000AFcd"))

    def test_ignores_comments(self):
        assert_that(self.stream_read(b"20 00 [comment]"), equal_to(b"2000"))

    def test_ignores_nested_comments(self):
        assert_that(self.stream_read(
            b"20 00 [ nested [comment] here ] FF"), equal_to(b"2000FF"))

    def test_newline_end_of_stream(self):
        assert_that(self.stream_read(
            b"20 00 [ nested [comment] here ]\n FF"), equal_to(b"2000"))

    def test_ignores_non_hex_chars(self):
        assert_that(self.stream_read(b"FfZfF"), equal_to(b"FffF"))

    def test_handles_empty_stream(self):
        assert_that(self.stream_read(b""), equal_to(b""))

    def test_flags(self):
        s = ChunkedHexTextInputStream(None)
        assert_that(s.writable(), is_(False))
        assert_that(s.readable(), is_(True))

    def test_read_or_peek_on_empty_stream_returns_empty(self):
        s = ChunkedHexTextInputStream(BufferedReader(io.BytesIO(b'a')))
        assert_that(s.peek(1), is_(equal_to(b'a')))
        assert_that(s.read(20), is_(equal_to(b'a')))
        assert_that(s.peek(1), is_(equal_to(b'')))
        assert_that(s.read(1), is_(equal_to(b'')))

    def stream_read(self, content):
        base = BufferedReader(io.BytesIO(content))
        text = ChunkedHexTextInputStream(base)
        return collect_stream(text)


class BinaryToHexOutputStreamTestCase(unittest.TestCase):

    def test_write_bytes(self):
        store = io.BytesIO()
        stream = self.create_stream(store)
        stream.write([129, 255])
        assert_that(store.getvalue(), is_(equal_to(b"81 FF ")))

    def test_write_annotation(self):
        store = io.BytesIO()
        stream = self.create_stream(store)
        stream.write_annotation(b"hello world")
        assert_that(store.getvalue(), is_(equal_to(b"[hello world]")))

    def test_write_bytes_and_annotation(self):
        store = io.BytesIO()
        stream = self.create_stream(store)
        stream.write_byte(129)
        stream.write_annotation(b"hello world")
        stream.write_byte(255)
        assert_that(store.getvalue(), is_(equal_to(b"81 [hello world]FF ")))

    def test_write_newline(self):
        store = io.BytesIO()
        stream = self.create_stream(store)
        stream.write_byte(129)
        stream.write_annotation(b"hello world")
        stream.newline()
        stream.write_byte(255)
        assert_that(store.getvalue(), is_(equal_to(b"81 [hello world]\nFF ")))

    def test_flags(self):
        store = io.BytesIO()
        s = self.create_stream(store)
        assert_that(s.writable(), is_(True))
        assert_that(s.readable(), is_(False))

    def create_stream(self, store):
        return BinaryToHexOutputStream(store)


class TextHexStreamTestCase(unittest.TestCase):

    def test_converts_hex_and_skips_spaces(self):
        assert_that(self.stream_read(b"20 01 40"),
                    is_(equal_to(b"\x20\x01\x40")))

    def test_bytes_must_contain_two_hex_digits(self):
        assert_that(self.stream_read(b"20 01 4"), is_(equal_to(b"\x20\x01")))

    def test_comments_ignored(self):
        assert_that(self.stream_read(
            b"20 [comment 01] 40"), is_(equal_to(b"\x20\x40")))

    def test_no_read_past_newline(self):
        stream = self.build_stream(b"12 34 \n 56")
        assert_that(collect_stream(stream), is_(equal_to(b"\x12\x34")))
        assert_that(collect_stream(stream), is_(equal_to(b"")),
                    "once a newline is received the stream should return no further data")
        # unwrap the hex stream and the text steam back to the binary buffer
        buffer = stream.detach().detach()
        assert_that(collect_stream(buffer), is_(equal_to(b" 56")))

    def test_can_read_past_newline_after_reset(self):
        stream = self.build_stream(b"12 34 \n 56  [12] ")
        assert_that(collect_stream(stream), is_(equal_to(b"\x12\x34")))
        assert_that(collect_stream(stream), is_(equal_to(b"")),
                    "once a newline is received the stream should return no further data")
        stream.stream.next_chunk()
        assert_that(collect_stream(stream), is_(equal_to(b"\x56")))
        buffer = stream.detach().detach()
        assert_that(collect_stream(buffer), is_(equal_to(b"")),
                    "expected base stream to be completely read")

    def test_read_bytes(self):
        stream = self.build_stream(b"12 34 \n 56  [12] ")
        assert_that(stream.read_next_byte(), is_(equal_to(0x12)))
        assert_that(stream.read_next_byte(), is_(equal_to(0x34)))
        assert_that(calling(stream.read_next_byte), raises(StopIteration))
        assert_that(stream.peek_next_byte(), is_(equal_to(-1)))
        stream.stream.next_chunk()
        assert_that(stream.peek_next_byte(), is_(0x56))
        assert_that(stream.read_next_byte(), is_(equal_to(0x56)))
        assert_that(calling(stream.read_next_byte), raises(StopIteration))

    def test_flags(self):
        s = self.build_stream(b"")
        assert_that(s.writable(), is_(False))
        assert_that(s.readable(), is_(True))

    def build_stream(self, content):
        base = BufferedReader(io.BytesIO(content))
        text = ChunkedHexTextInputStream(base)
        hexstream = HexToBinaryInputStream(text)
        return hexstream

    def stream_read(self, content):
        hexstream = self.build_stream(content)
        return collect_stream(hexstream)


class BrewpiV030ProtocolSendRequestTestCase(unittest.TestCase):

    def setUp(self):
        self.conduit = DefaultConduit(BytesIO(), BytesIO())
        self.sut = ControllerProtocolV030(self.conduit, lambda: None)

    def test_send_read_command_bytes(self):
        future = self.sut.read_value([1, 2, 3])
        self.assert_request_sent(1, 0x81, 0x82, 3, 0)

    def test_send_write_command_bytes(self):
        future = self.sut.write_value([1, 2, 3], [4, 5])
        self.assert_request_sent(2, 0x81, 0x82, 3, 2, 4, 5)

    def test_send_create_object_command_bytes(self):
        future = self.sut.create_object([1, 2, 3], 27, [4, 5, 6])
        self.assert_request_sent(3, 0x81, 0x82, 3, 27, 3, 4, 5, 6)

    def test_send_delete_object_command_bytes(self):
        future = self.sut.delete_object([1, 2])
        self.assert_request_sent(4, 0x81, 2)

    def test_send_list_profile_command_bytes(self):
        future = self.sut.list_profile(4)
        self.assert_request_sent(5, 4)

    def test_send_next_slot_object_command_bytes(self):
        future = self.sut.next_slot([1, 4])
        self.assert_request_sent(6, 0x81, 4)

    def assert_request_sent(self, *args):
        expected = bytes(args)
        actual = self.conduit.output.getvalue()
        assert_that(actual, equal_to(expected))


def assert_future(future, match):
    assert_that(future.done(), is_(True), "expected future to be complete")
    assert_that(future.value(), match)


class BrewpiV030ProtocolDecodeResponseTestCase(unittest.TestCase):

    def setUp(self):
        self.input_buffer = RWCacheBuffer()
        self.output_buffer = RWCacheBuffer()
        self.conduit = DefaultConduit(
            self.input_buffer.reader, self.output_buffer.writer)
        self.sut = ControllerProtocolV030(self.conduit)

    def test_send_read_command_bytes(self):
        future = self.sut.read_value([1, 2, 3])
        # emulate a on-wire response
        self.push_response([1, 0x81, 0x82, 3, 0, 2, 4, 5])
        assert_future(future, is_(equal_to(bytes([4, 5]))))

    def test_resposne_must_match(self):
        """ The command ID is the same but the request data is different. So this doesn't match up with the previous.
            Request. """
        future = self.sut.read_value([1, 2, 3])
        self.push_response([1, 0x81, 0x82, 0, 4, 2, 4, 5])
        assert_that(future.done(), is_(False))

    def test_multiple_outstanding_requests(self):
        """ Tests the requests are matched as the corresponding repsonses are received."""
        future1 = self.sut.read_value([1, 2, 3])
        future2 = self.sut.read_value([1, 2, 4])

        # push all the data, to be sure that
        self.push_response([1, 0x81, 0x82, 4, 0, 2, 2, 3]
                           )         # matches request 2
        assert_future(future2, is_(equal_to(bytes([2, 3]))))
        assert_that(future1.done(), is_(False))
        self.push_response([1, 0x81, 0x82, 3, 0, 3, 4, 5, 6]
                           )      # matches request 1
        assert_future(future1, is_(equal_to(bytes([4, 5, 6]))))

    def push_response(self, data):
        self.input_buffer.writer.write(bytes(data))
        self.input_buffer.writer.flush()
        self.sut.read_response()


class BrewpiV030ProtocolHexEncodingTestCase(unittest.TestCase):
    """ A more complete test where multiple commands are sent, and the on-wire hex-encoded values are used. """

    def setUp(self):
        self.input_buffer = RWCacheBuffer()
        self.output_buffer = RWCacheBuffer()
        # this represents the far end of the pipe - input/output bytes sent as
        # hex encoded binary
        self.conduit = DefaultConduit(
            self.input_buffer.reader, self.output_buffer.writer)
        text = build_chunked_hexencoded_conduit(self.conduit)
        self.sut = ControllerProtocolV030(*text)

    def tearDown(self):
        self.input_buffer.close()
        self.output_buffer.close()

    def test_send_read_command_bytes(self):
        future = self.sut.read_value([1, 2, 3])
        # NB: this is ascii encoded hex now, not binary data
        self.assert_request_sent(b'01 81 82 03 00 \n')

    def test_full_read_command_bytes(self):
        future = self.sut.read_value([1, 2, 3])
        # emulate the response
        self.push_response(b'01 81 82 03 00 01 aB CD \n')
        assert_future(future, is_(equal_to(bytes([0xAB]))))

    def push_response(self, data):
        self.input_buffer.writer.write(bytes(data))
        self.input_buffer.writer.flush()
        self.sut.read_response()

    def assert_request_sent(self, expected):
        actual = self.output_buffer.reader.readlines()[0]
        assert_that(actual, equal_to(expected))


if __name__ == '__main__':
    unittest.main()
