from abc import abstractmethod, ABCMeta
from io import IOBase, BytesIO, BufferedIOBase
from conduit.base import Conduit, DefaultConduit
from protocol.async import BaseAsyncProtocolHandler, FutureResponse, Request, Response, ResponseSupport
from protocol.version import VersionParser


def unsigned_byte(val):
    """ converts an unsigned byte to a corresponding 2's complement signed value
    >>> unsigned_byte(0)
    0
    >>> unsigned_byte(-1)
    255
    >>> unsgined_byte(127)
    127
    >>> unsigned_byte(-128)
    128
    """
    return val if val >= 0 else val + 256


def signed_byte(b):
    """ converts an unsigned byte to a corresponding 2's complement signed value
    >>> signed_byte(0)
    0
    >>> signed_byte(255)
    -1
    >>> signed_byte(127)
    127
    >>> signed_byte(128)
    -128
    """
    return b if b < 128 else b - 256


def brewpi_v03x_protocol_sniffer(line, conduit):
    result = None
    line = line.strip()
    if line.startswith("[") and line.endswith("]"):
        info = VersionParser("{" + line[1:-1] + "}")
        if info.major == 0 and info.minor == 3:
            if info.revision == 0:
                result = BrewpiProtocolV030(*build_chunked_hexencoded_conduit(conduit))
    return result


def encode_id(idchain) -> bytearray:
    """
    Encodes a sequence of integers to the on-wire binary values (before hex encoding.)

    >>> list(encode_id([1]))
    [1]

    >>> list(encode_id([1,2,3]))
    [129, 130, 3]

    >>> encode_id([])
    bytearray(b'')

    :return:converts a byte array representing an id chain to the comms format.
    :rtype:
    """
    l = len(idchain)
    result = bytearray(l)
    for x in range(0, l - 1):
        result[x] = idchain[x] | 0x80
    if l > 0:
        result[l - 1] = idchain[l - 1]
    return result


class ByteArrayRequest(Request):
    """ represents a request as an array or bytes. The byte array defines the key for the reuqest, since responses
        always repeat the request data verbatim. """

    def __init__(self, data):
        self.data = data

    def to_stream(self, file):
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

    # noinspection PyUnusedLocal
    def peek(self, *args, **kwargs):
        return bytes([self._decode_next_byte()]) if self.has_next() else bytes()

    # noinspection PyUnusedLocal
    def read(self, *args, **kwargs):
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

    def __init__(self, stream):
        super().__init__()
        if not stream.writable():
            raise ValueError()
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
        self.data = None
        self.stream = stream
        self.comment_level = 0
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
        self.buffer = BytesIO()
        self.stream = stream

    def push(self, data):
        self.buffer.write(data)

    def read(self, count=-1):
        b = self.stream.read(count)
        self.buffer.write(b)
        return b

    def peek(self, count=0):
        return self.stream.peek(count)

    def peek_next_byte(self):
        return self.stream.peek_next_byte()

    def as_bytes(self):
        return bytes(self.buffer.getbuffer())

    def close(self):
        pass


class Commands:
    no_cmd = 0
    read_value = 1
    write_value = 2
    create_object = 3
    delete_object = 4
    list_profile = 5
    next_free_slot = 6
    create_profile = 7
    delete_profile = 8
    activate_profile = 9
    log_values = 0xA
    reset = 0xB
    next_free_slot_root = 0xC
    list_profiles = 0xE
    read_system_value = 0xF
    write_system_value = 0x10
    list_system_values = 0x11


# A note to maintainers: These ResponseDecoder objects have to be written carefully - the
# _parse and decode_response methods have to match exactly the command request and command response
# If _parse doesn't consume the right amount of bytes, the response will not be matched up with the
# corresponding request, and the caller will never get a response (and will eventually timeout on the
# FutureRequest.)


class ResponseDecoder(metaclass=ABCMeta):
    """  parses the response data into the data block corresponding to the original request
         and decodes the data block that is the additional response data
    """

    def decode_request(self, cmd_id: int, stream: BufferedIOBase):
        """ read the portion of the response that corresponds to the original request. """
        buf = CaptureBufferedReader(stream)
        buf.push(bytes([cmd_id]))
        self._parse(buf)
        return buf.as_bytes()

    @abstractmethod
    def _parse(self, buf):
        pass

    def _read_id_chain(self, buf):
        result = bytearray()
        while buf.peek_next_byte() >= 0:
            b = self._read_byte(buf)
            result.append(b & 0x7F)
            if b < 0x80:
                break
        return result

    def _read_vardata(self, stream):
        """ decodes variable length data from the stream. The first byte is the number of bytes in the data block,
            followed by N bytes that make up the data block.
        """
        size = self._read_byte(stream)
        buf = bytearray(size)
        idx = 0
        while idx < size:
            buf[idx] = self._read_byte(stream)
            idx += 1
        return bytes(buf)

    @staticmethod
    def _read_signed_byte(stream):
        b = ResponseDecoder._read_byte(stream)
        return signed_byte(b)

    @staticmethod
    def _read_byte(stream):
        """ reads the next byte from the stream. If there is no more data, an exception is thrown.
            bytes are returned as unsigned. """
        b = stream.read(1)
        if not b:
            raise ValueError
        return b[0]

    def _read_status_code(self, stream):
        """ parses and returns a status-code """
        return self._read_signed_byte(stream)

    def _read_object_defn(self, buf):
        id_chain = self._read_id_chain(buf)  # the location to create the object
        obj_type = self._read_byte(buf)  # the type of the object
        ctor_params = self._read_vardata(buf)  # the object constructor data block
        return id_chain, obj_type, ctor_params

    def _read_object_value(self, buf):
        id_chain = self._read_id_chain(buf)  # the location to create the object
        ctor_params = self._read_vardata(buf)  # the object constructor data block
        return id_chain, ctor_params

    def _read_remainder(self, stream):
        """ reads the remaining bytes in the stream into a list """
        values = []
        while stream.peek_next_byte() >= 0:  # has more data
            value = self._read_byte(stream)
            values.append(value)
        return values

    @abstractmethod
    def decode_response(self, stream):
        pass


class ReadValueResponseDecoder(ResponseDecoder):
    def _parse(self, buf):
        # read the id of the objec to read
        self._read_id_chain(buf)
        self._read_byte(buf)  # length of data expected

    def decode_response(self, stream):
        """ The read command response is a single variable length buffer. """
        return self._read_vardata(stream)


class WriteValueResponseDecoder(ResponseDecoder):
    def _parse(self, buf):
        self._read_id_chain(buf)  # id chain
        len = self._read_vardata(buf)  # length and body of data to write

    def decode_response(self, stream):
        """ The write command response is a single variable length buffer indicating the value written. """
        return self._read_vardata(stream)


class CreateObjectResponseDecoder(ResponseDecoder):
    def _parse(self, buf):
        self._read_object_defn(buf)

    def decode_response(self, stream):
        """ The create object command response is a status code. """
        return self._read_status_code(stream)


class DeleteObjectResponseDecoder(ResponseDecoder):
    def _parse(self, buf):
        self._read_id_chain(buf)  # the location of the object to delete

    def decode_response(self, stream):
        """ The delete object command response is a status code. """
        return self._read_status_code(stream)


class ListProfileResponseDecoder(ResponseDecoder):
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


class NextFreeSlotResponseDecoder(ResponseDecoder):
    def _parse(self, buf):
        self._read_id_chain(buf)  # the container to find the next free slot

    def decode_response(self, stream):
        """ The next free slot command response is a byte indicating the next free slot. """
        return self._read_status_code(stream)


class NextFreeSlotRootResponseDecoder(ResponseDecoder):
    def _parse(self, buf):  # additional command arguments to read
        pass

    def decode_response(self, stream):
        """ The next free slot command response is a byte indicating the next free slot. """
        return self._read_status_code(stream)


class CreateProfileResponseDecoder(ResponseDecoder):
    def _parse(self, buf):
        pass  # no additional command parameters

    def decode_response(self, stream):
        """ Returns the new profile id or negative on error. """
        return self._read_status_code(stream)


class DeleteProfileResponseDecoder(ResponseDecoder):
    def _parse(self, buf):
        self._read_byte(buf)  # profile_id

    def decode_response(self, stream):
        """ Result is a status code. """
        return self._read_status_code(stream)


class ActivateProfileResponseDecoder(ResponseDecoder):
    def _parse(self, buf):
        self._read_byte(buf)  # profile id

    def decode_response(self, stream):
        """ Returns the active profile id or negative on error. """
        return self._read_status_code(stream)


class ListProfilesResponseDecoder(ResponseDecoder):
    def _parse(self, buf):
        pass  # no additional command arguments

    def decode_response(self, stream):
        r = self._read_remainder(stream)  # read active profile followed by available profiles
        r[0] = signed_byte(r[0])  # active profile is signed
        return r


class ResetResponseDecoder(ResponseDecoder):
    def _parse(self, buf):  # additional command arguments to read
        self._read_byte(buf)  # flags

    def decode_response(self, stream):
        """ Returns a status code. """
        return self._read_status_code(stream)


class LogValuesResponseDecoder(ResponseDecoder):
    def _parse(self, buf):
        flag = self._read_byte(buf)  # flag to indicate if an id is needed
        if flag:
            self._read_id_chain(buf)  # the id

    def decode_response(self, stream):
        """ Returns the new profile id or negative on error. """
        return self._read_remainder(stream)


class ReadSystemValueCommandDecoder(ReadValueResponseDecoder):
    pass


class WriteSystemValueCommandDecoder(WriteValueResponseDecoder):
    pass


class ListSystemValuesCommandDecoder(ListProfileResponseDecoder):
    pass


def build_chunked_hexencoded_conduit(conduit):
    """ Builds a binary conduit that converts the binary data to ascii-hex digits.
        Input/Output are chunked via newlines. """
    chunker = ChunkedHexTextInputStream(conduit.input)
    hex_in = HexToBinaryInputStream(chunker)
    hex_out = BinaryToHexOutputStream(conduit.output)

    def next_chunk_input():
        chunker.next_chunk()

    def next_chunk_output():
        hex_out.newline()

    return DefaultConduit(hex_in, hex_out), next_chunk_input, next_chunk_output


def nop():
    pass



class BrewpiProtocolV030(BaseAsyncProtocolHandler):
    """ Implements the v2 hex-encoded binary protocol. """

    decoders = {
        Commands.read_value: ReadValueResponseDecoder,
        Commands.write_value: WriteValueResponseDecoder,
        Commands.create_object: CreateObjectResponseDecoder,
        Commands.delete_object: DeleteObjectResponseDecoder,
        Commands.list_profile: ListProfileResponseDecoder,
        Commands.next_free_slot: NextFreeSlotResponseDecoder,
        Commands.create_profile: CreateProfileResponseDecoder,
        Commands.delete_profile: DeleteProfileResponseDecoder,
        Commands.activate_profile: ActivateProfileResponseDecoder,
        Commands.reset: ResetResponseDecoder,
        Commands.log_values: LogValuesResponseDecoder,
        Commands.next_free_slot_root: NextFreeSlotRootResponseDecoder,
        Commands.list_profiles: ListProfilesResponseDecoder,
        Commands.read_system_value: ReadSystemValueCommandDecoder,
        Commands.write_system_value: WriteSystemValueCommandDecoder,
        Commands.list_system_values: ListSystemValuesCommandDecoder
    }

    def __init__(self, conduit: Conduit,
                 next_chunk_input=nop, next_chunk_output=nop):
        """ The conduit is assumed to read/write binary data. This class doesn't concern itself with the
            low-level encoding, such as hex-coded bytes. """
        super().__init__(conduit)
        self.input = conduit.input
        self.output = conduit.output
        self.next_chunk_input = next_chunk_input
        self.next_chunk_output = next_chunk_output

    def read_value(self, id_chain, expected_len) -> FutureResponse:
        """ requests the value of the given object id is read. """
        return self._send_command(Commands.read_value, encode_id(id_chain), expected_len)

    def write_value(self, id_chain, buf) -> FutureResponse:
        return self._send_command(Commands.write_value, encode_id(id_chain), len(buf), buf)

    def create_object(self, id_chain, object_type, data) -> FutureResponse:
        return self._send_command(Commands.create_object, encode_id(id_chain), object_type, len(data), data)

    def delete_object(self, id_chain) -> FutureResponse:
        return self._send_command(Commands.delete_object, encode_id(id_chain))

    def list_profile(self, profile_id) -> FutureResponse:
        return self._send_command(Commands.list_profile, profile_id)

    def next_slot(self, id_chain) -> FutureResponse:
        return self._send_command(Commands.next_free_slot if len(id_chain) else Commands.next_free_slot_root,
                                  encode_id(id_chain))

    def reset(self, flags) -> FutureResponse:
        return self._send_command(Commands.reset, flags)

    def create_profile(self) -> FutureResponse:
        return self._send_command(Commands.create_profile)

    def delete_profile(self, profile_id) -> FutureResponse:
        return self._send_command(Commands.delete_profile, profile_id)

    def activate_profile(self, profile_id) -> FutureResponse:
        return self._send_command(Commands.activate_profile, profile_id)

    def list_profiles(self) -> FutureResponse:
        return self._send_command(Commands.list_profiles)

    def read_system_value(self, id_chain, expected_len):
        return self._send_command(Commands.read_system_value, encode_id(id_chain), expected_len)

    def write_system_value(self, id_chain, buf) -> FutureResponse:
        return self._send_command(Commands.write_system_value, encode_id(id_chain), len(buf), buf)

    def list_system_values(self) -> FutureResponse:
        return self._send_command(Commands.list_system_values)

    @staticmethod
    def build_bytearray(*args):
        """
        constructs a byte array from position arguments.
        >>> BrewpiProtocolV030.build_bytearray(90, b"\x42\x43", 95)
        bytearray(b'ZBC_')
        """
        b = bytearray()
        for arg in args:
            try:
                for val in arg:
                    b.append(unsigned_byte(val))
            except TypeError:
                b.append(unsigned_byte(arg))
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
        """ reads the next response from the conduit. Blocks until data is available. """
        self.next_chunk_input()  # move onto next chunk after newline
        stream = self.input
        next_byte = stream.read(1)
        if next_byte:
            cmd_id = next_byte[0]
            try:
                if cmd_id:  # peek command id
                    decoder = self._create_response_decoder(cmd_id)
                    command_block = decoder.decode_request(cmd_id, stream)
                    try:
                        value = decoder.decode_response(stream)
                        if value is None:
                            raise ValueError("request decoder did not return a value")
                    except Exception as e:
                        value = e
                    return ResponseSupport(command_block, value)
            finally:
                while not stream.closed and stream.read():  # spool off rest of block if caller didn't read it
                    pass

    @staticmethod
    def _create_response_decoder(cmd_id):
        decoder_type = BrewpiProtocolV030.decoders.get(cmd_id)
        if not decoder_type:
            raise ValueError("no decoder for cmd_id %d" % cmd_id)
        return decoder_type()
