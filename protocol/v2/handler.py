from abc import abstractmethod
from io import IOBase, BufferedReader
import io
from conduit.base import Conduit, DefaultConduit
from protocol.async import BaseAsyncProtocolHandler, FutureResponse, Request, Response, ResponseSupport


def encodeId(idChain) -> bytearray:
    """
    Encodes a sequence of integers to the on-wire binary values (before hex encoding.)

    >>> list(encodeId([1]))
    [1]

    >>> list(encodeId([1,2,3]))
    [129, 130, 3]

    >>> encodeId([])
    bytearray(b'')

    :return:converts a byte array representing an id chain to the comms format.
    :rtype:
    """
    l = len(idChain)
    result = bytearray(l)
    for x in range(0, l - 1):
        result[x] = idChain[x] | 0x80
    if (l > 0):
        result[l - 1] = idChain[l - 1]
    return result


class ByteArrayRequest(Request):
    """ represents a request as an array or bytes. The byte array defines the key for the reuqest, since responses
        always repeat the request data verbatim. """

    def __init__(self, data:bytes):
        self.data = data

    def to_stream(self, file: IOBase):
        file.write(self.data)

    @property
    def response_keys(self):
        """ the commands requests and responses are structured such that the entire command request is the unique key
            for the command """
        return [self.data]


def h2b(h):
    """
    :param h: The hex digit to convert to binary, as an int
    :return: A binary value from 0-15

    >>> h2b('0')
    0
    >>> h2b('9')
    9
    >>> h2b('A')
    10
    >>> h2b('f')
    15
    >>> h2b('F')
    15

    """
    b = ord(h)
    if h > '9':
        b -= 7  # // 'A' is 0x41, 'a' is 0x61. -7 =  0x3A, 0x5A
    return b & 0xF


def b2h(b):
    """ Converts a binary nibble (0-15) to a hex digit
    :param b: the binary value to convert to a hex digit
    :return: the corresponding hex digit
    >>> b2h(0)
    '0'
    >>> b2h(9)
    '9'
    >>> b2h(10)
    'A'
    >>> b2h(15)
    'F'
    """
    return chr(b + (ord('0') if b <= 9 else ord('A') - 10))


class HexToBinaryInputStream(IOBase):
    """ converts from hex-encoded bytes (ascii) to byte values.
        The stream automatically closes when a newline is detected, and ensures that the underlying stream
        is not read past the newline. This allows the code constructing the stream to limit clients reading
        from the stream to one logical command.
    """

    def __init__(self, stream, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.char1 = 0
        self.char2 = 0
        self.stream = stream

    def close(self):
        pass

    def has_next(self):
        self._fetch_next_byte()
        return self.char1 != 0

    def _consume_byte(self):
        self.char1 = 0

    def read_next_byte(self):
        if not self.has_next():
            raise StopIteration()
        result = self._decode_next_byte()
        self._consume_byte()
        return result

    def peek_next_byte(self):
        if not self.has_next():
            return -1
        return self._decode_next_byte()

    def peek(self, count=0):
        return bytes([self._decode_next_byte()]) if self.has_next() else bytes()

    def read(self, count=-1):
        result = self.peek(1)
        self._consume_byte()
        return result

    def _fetch_next_byte(self):
        if self.char1 != 0:  # already have a character
            return

        b1 = self.stream.read(1)
        b2 = self.stream.read(1)
        if b1 and b2:
            self.char1 = chr(b1[0])
            self.char2 = chr(b2[0])

    def detach(self):
        result = self.stream
        self.stream = None
        return result

    def readable(self, *args, **kwargs):
        return True

    def _decode_next_byte(self):
        return (h2b(self.char1) * 16) | h2b(self.char2)


class BinaryToHexOutputStream(IOBase):
    """ A binary stream that writes data as two hex-encoded digits."""

    def __init__(self, stream, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stream = stream

    def write_annotation(self, annotation):
        self._write_byte(ord('['))
        self.stream.write(annotation)
        self._write_byte(ord(']'))

    def write_byte(self, b):
        self._write_byte(ord(b2h(b >> 4)))
        self._write_byte(ord(b2h(b & 0xF)))
        self._write_byte(ord(' '))

    def write(self, buf):
        for b in buf:
            self.write_byte(b)

    def _write_byte(self, b):
        """write a byte directly to the stream"""
        buf = bytearray(1)
        buf[0] = b
        self.stream.write(buf)

    def newline(self):
        self._write_byte(ord('\n'))
        self.stream.flush()

    def detach(self):
        result = self.stream
        self.stream = None
        return result

    def writable(self, *args, **kwargs):
        return True


def is_hex_digit(val):
    return ord('0') <= val <= ord('9') or ord('A') <= val <= ord('F') or ord('a') <= val <= ord('f')


class ChunkedHexTextInputStream(IOBase):
    """ Reads a binary stream that encodes ascii text. non-hex characters are discarded, newlines terminate
        a block - the caller should call reset() to move to the next block. Commants enclosed in [] are ignored. """
    no_data = bytes()

    def __init__(self, stream, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stream = stream
        self.next_chunk()

    def read(self, count=-1):
        if not count:
            return ChunkedHexTextInputStream.no_data
        self.fetch_next()
        result = self.data
        self.data = ChunkedHexTextInputStream.no_data
        return result

    def peek(self, count=0):
        if not count:
            return ChunkedHexTextInputStream.no_data
        self.fetch_next()
        return self.data

    def fetch_next(self):
        while not self.data and self.comment_level >= 0 and self._stream_has_data():
            d = self.stream.read(1)
            if d == b'[':
                self.comment_level += 1
            elif d == b']':
                self.comment_level -= 1
            elif d == b'\n':
                self.comment_level = -1
            elif not self.comment_level and is_hex_digit(d[0]):
                self.data = d

    def _stream_has_data(self):
        return self.stream.peek(1)

    def detach(self):
        result = self.stream
        self.stream = None
        return result

    def readable(self, *args, **kwargs):
        return True

    def next_chunk(self):
        """ advances after a newline so that callers can read subsequent data. """
        self.data = ChunkedHexTextInputStream.no_data
        self.comment_level = 0


class CaptureBufferedReader:
    def __init__(self, stream):
        self.buffer = io.BytesIO()
        self.stream = stream

    def read(self, count=-1):
        b = self.stream.read(count)
        self.buffer.write(b)
        return b

    def peek(self, count=0):
        return self.stream.peek(count)

    def as_bytes(self):
        return bytes(self.buffer.getbuffer())

    def close(self):
        pass


def _buffer(result):
    pass


class Commands:
    no_cmd = 0
    read_value = 1
    write_value = 2
    create_object = 3
    delete_object = 4
    list_objects = 5
    next_free_slot = 6
    create_profile = 7
    delete_profile = 8
    compact_profile = 9
    log_values = 10
    reset = 11


class CommandDecoder:
    def decode_command(self, stream:io.BufferedIOBase):
        buf = CaptureBufferedReader(stream)
        cmd_id = self._read_byte(buf)  # todo - could validate this command ID just to be sure.
        self._parse(buf)
        return buf.as_bytes()

    @abstractmethod
    def _parse(self, buf):
        pass

    def _read_id_chain(self, buf):
        result = bytearray()
        while self._peek_next_byte(buf) >= 0:
            b = self._read_byte(buf)
            result.append(b & 0x7F)
            if b < 0x80:
                break
        return result

    def _read_vardata(self, stream):
        """ decodes variable length data from the stream. The first byte is the number of bytes in the data block,
            followed by N bytes that make up the data block.
        """
        len = self._read_byte(stream)
        buf = bytearray(len)
        idx = 0
        while idx < len:
            buf[idx] = self._read_byte(stream)
            idx += 1
        return buf

    @staticmethod
    def _read_byte(stream):
        """ reads the next byte from the stream. If there is no more data, an exception is thrown. """
        b = stream.read(1)
        if not b:
            raise ValueError
        return b[0]

    def _read_status_code(self, stream):
        """ parses and returns a status-code """
        return self._read_byte(stream)

    def _read_object_defn(self, buf):
        id_chain = self._read_id_chain(buf)  # the location to create the object
        obj_type = self._read_byte(buf)  # the type of the object
        ctor_params = self._read_vardata(buf)  # the object constructor data block
        return id_chain, obj_type, ctor_params

    def _read_value(self, buf):
        id_chain = self._read_id_chain(buf)  # the location to create the object
        ctor_params = self._read_vardata(buf)  # the object constructor data block
        return id_chain, ctor_params


    @abstractmethod
    def decode_response(self, stream):
        pass

    def _peek_next_byte(self, stream):
        b = stream.peek(1)
        return b[0]


class ReadValueCommandDecoder(CommandDecoder):
    def _parse(self, buf):
        # read the id of the objec to read
        id_chain = self._read_id_chain(buf)

    def decode_response(self, stream):
        """ The read command response is a single variable length buffer. """
        return self._read_vardata(stream)


class WriteValueCommandDecoder(CommandDecoder):
    def _parse(self, buf):
        self._read_value(buf)

    def decode_response(self, stream):
        """ The write command response is a single variable length buffer indicating the value written. """
        return self._read_vardata(stream)


class CreateObjectCommandDecoder(CommandDecoder):
    def _parse(self, buf):
        self._parse_object_defn(buf)

    def decode_response(self, stream):
        """ The create object command response is a status code. """
        return self._read_status_code(stream)


class DeleteObjectCommandDecoder(CommandDecoder):
    def _parse(self, buf):
        id_chain = self._read_id_chain(buf)  # the location of the object to delete

    def decode_response(self, stream):
        """ The delete object command response is a status code. """
        return self._read_status_code(stream)


class ListObjectsCommandDecoder(CommandDecoder):
    def _parse(self, buf):
        pass  # no additional command data in the original request

    def decode_response(self, stream):
        """ retrieves a list of tuples (id, type, data) """
        values = []
        while stream.peek_next_byte() >= 0:  # has more data
            b = stream.read_next_byte()
            if b != Commands.create_object:
                raise ValueError()
            obj_defn = self._read_object_defn(stream)
            values.append(obj_defn)
        return values


class NextFreeSlotCommandDecoder(CommandDecoder):
    def _parse(self, buf):
        container = self._parse_id_chain(buf)  # the container to find the next free slot

    def decode_response(self, stream):
        """ The next free slot command response is a byte indicating the next free slot. """
        return self._read_status_code(stream)


class CreateProfileCommandDecoder(CommandDecoder):
    def _parse(self, buf):
        pass  # no additional command parameters

    def decode_response(self, stream):
        """ Returns the new profile id or negative on error. """
        return self._read_status_code(stream)


class DeleteProfileCommandDecoder(CommandDecoder):
    def _parse(self, buf):
        profile_id = self._read_byte(buf)

    def decode_response(self, stream):
        """ Result is a status code. """
        return self._read_status_code(stream)


class CompactStorageCommandDecoder(CommandDecoder):
    def _parse(self, buf):
        pass  # no additional command parameters

    def decode_response(self, stream):
        """ Returns the new profile id or negative on error. """
        return self._read_status_code(stream)


class LogValuesCommandDecoder(CommandDecoder):
    def _parse(self, buf):
        flag = self._read_byte(buf)
        id = None
        if flag:
            id = self._read_id_chain(buf)

    def decode_response(self, stream):
        """ Returns the new profile id or negative on error. """
        values = []
        while stream.peek_next_byte() >= 0:  # has more data
            value = self._read_value(stream)
            values.append(value)
        return values


def build_chunked_hexencoded_conduit(conduit):
    """ Builds a binary conduit that converts the binary data to ascii-hex digits.
        Input/Output are chunked via newlines. """
    chunker = ChunkedHexTextInputStream(conduit.input)
    input = HexToBinaryInputStream(chunker)
    output = BinaryToHexOutputStream(conduit.output)

    def next_chunk_input():
        chunker.next_chunk()

    def next_chunk_output():
        output.newline()

    return DefaultConduit(input, output), next_chunk_input, next_chunk_output

def nop():
    pass

class BrewpiV2Protocol(BaseAsyncProtocolHandler):
    """ Implements the v2 hex-encoded binary protocol. """

    decoders = {
        Commands.read_value: ReadValueCommandDecoder,
        Commands.write_value: WriteValueCommandDecoder,
        Commands.create_object: CreateObjectCommandDecoder,
        Commands.delete_object: DeleteObjectCommandDecoder,
        Commands.list_objects: ListObjectsCommandDecoder,
        Commands.next_free_slot: NextFreeSlotCommandDecoder,
        Commands.create_profile: CreateProfileCommandDecoder,
        Commands.delete_profile: DeleteProfileCommandDecoder,
        Commands.compact_profile: CompactStorageCommandDecoder,
        Commands.log_values: LogValuesCommandDecoder
    }

    def __init__(self, conduit: Conduit, next_chunk_input:callable=nop, next_chunk_output:callable=nop):
        """ The conduit is assumed to read/write binary data. This class doesn't concern itself with the
            low-level encoding, such as hex-coded bytes. """
        super().__init__(conduit)
        self.input = conduit.input
        self.output = conduit.output
        self.next_chunk_input = next_chunk_input
        self.next_chunk_output = next_chunk_output

    def read_value(self, id) -> FutureResponse:
        """ requests the value of the given object id is read. """
        return self._send_command(Commands.read_value, encodeId(id))

    def write_value(self, id, buf) -> FutureResponse:
        return self._send_command(Commands.write_value, encodeId(id), len(buf), buf)

    def create_object(self, id, object_type, data) -> FutureResponse:
        return self._send_command(Commands.create_object, encodeId(id), object_type, len(data), data)

    def delete_object(self, id) -> FutureResponse:
        return self._send_command(Commands.delete_object, encodeId(id))

    def list_objects(self, id) -> FutureResponse:
        return self._send_command(Commands.list_objects, encodeId(id))

    def next_slot(self, id) -> FutureResponse:
        return self._send_command(Commands.next_free_slot, encodeId(id))

    @staticmethod
    def build_bytearray(*args):
        """
        constructs a byte array from position arguments.
        >>> BrewpiV2Protocol.build_bytearray(90, b"\x42\x43", 95)
        bytearray(b'ZBC_')
        """
        b = bytearray()
        for arg in args:
            try:
                for val in arg:
                    b.append(val)
            except TypeError:
                b.append(arg)
        return b

    def _send_command(self, *args):
        """
            Sends a command. the command is made up of all the arguments. Either an argument is a simple type, which is
            converted to a byte or it is a list type whose elements are converted to bytes.
            The command is sent synchronously and the result is returned. The command may timeout.
        """
        cmd_bytes = bytes(self.build_bytearray(*args))
        request = ByteArrayRequest(cmd_bytes)
        return self.async_request(request)

    def _stream_request_sent(self, request):
        """ notification that a request has been sent. move the output onto the next chunk. """
        self.next_chunk_output()


    def _decode_response(self) -> Response:
        """ reads the next response from the conduit. """
        self.next_chunk_input()  # move onto next chunk after newline
        stream = self.input
        next = stream.peek(1)
        if next and next[0]:  # <0 means no data available yet
            try:
                decoder = self._create_response_decoder(next[0])
                command_block = decoder.decode_command(stream)
                value = decoder.decode_response(stream)
                return ResponseSupport(command_block, value)
            finally:
                while not stream.closed and stream.read():  # spool off rest of block if caller didn't read it
                    pass

    @staticmethod
    def _create_response_decoder(cmd_id):
        decoder_type = BrewpiV2Protocol.decoders.get(cmd_id)
        return decoder_type()

