from io import BufferedIOBase
import json
from abc import abstractmethod
from protocol.async import FutureValue, Request, BaseAsyncProtocolHandler, FutureResponse, Response, tobytes
from protocol.version import VersionParser

__author__ = 'mat'


def brewpi_v02x_protocol_sniffer(line, conduit):
    result = None
    if line.startswith("N:"):
        info = VersionParser(line[2:])
        if info.major == 0 and info.minor == 2:
            if info.revision == 3:
                return ControllerProtocolV023(conduit)
    elif len(line) > 1 and line[1] == ':':  # hack for old versions
        return ControllerProtocolV023(conduit)
    return result


class CharacterLCDInfo:
    """ describes an LCD attached to the controller
    """

    def __init__(self, width, height):
        self.width = width
        self.height = height

    @property
    def dimensions(self):
        return self.width, self.height


class MessageFormat:
    """ Describes a way to convert a streamed message to and from an object representation """

    @abstractmethod
    def scan(self, reader):
        """
        :param reader: the stream to read subsequent bytes from. Bytes can be peeked, and not consumed.
        :return: an object representing the scanned message format
        """
        pass

    @abstractmethod
    def produce(self, item, writer):
        pass


class JSONFormat(MessageFormat):
    def produce(self, item, writer):
        out = json.dumps(item)
        writer.write(tobytes(out))

    def scan(self, reader):
        """assumes line based reader"""
        line = reader.readline()
        parsed = json.loads(line.decode('ascii'))
        return parsed


class VersionFormat(MessageFormat):
    def scan(self, reader):
        line = reader.readline()
        return VersionParser(line)

    def produce(self, item, writer):
        raise NotImplementedError


class LCDDisplayFormat(MessageFormat):
    def produce(self, item, writer):
        pass

    def scan(self, reader):
        pass


class LogMessageFormat(MessageFormat):
    def produce(self, item, writer):
        pass

    def scan(self, reader):
        pass


class BaseDef(object):
    char = None
    name = None
    format_type = None


class RequestDef(BaseDef):
    responses = None


class ResponseDef(BaseDef):
    pass


def request_def(char, name, format_type, responses):
    return make_dynamic(locals(), RequestDef())


def response_def(char, name, format_type):
    return make_dynamic(locals(), ResponseDef())


def make_dynamic(d, target):
    for x, y in d.items():
        setattr(target, x, y)
    return target


def defs_as_dict(*defs):
    """ creates a map from request/response code to the request/response tuple """
    return dict((d.char, d) for d in defs)


class MessageRequest(Request):
    def __init__(self, defn: RequestDef, value=None):
        self.defn = defn
        self.value = value

    @property
    def response_keys(self):
        return self.defn.responses

    def to_stream(self, file: BufferedIOBase):
        """
         streams the request character, and optionally any additional data required by the message format and value
        """
        file.write(self.defn.char)
        mf = self.defn.format_type
        value = self.value
        if mf is not None and value is not None:
            mf.produce(value, file)
        file.write(b'\n')


class MessageResponse(Response):
    def __init__(self, defn):
        self.defn = defn
        self._value = None

    def from_stream(self, file):
        if self.defn.format_type is not None:
            self._value = self.defn.format_type.scan(file)

    @property
    def response_key(self):
        return self.defn.char

    @property
    def value(self):
        return self._value


class ControllerProtocolV023(BaseAsyncProtocolHandler):
    JSONFormat.instance = JSONFormat()

    requests = defs_as_dict(
        request_def(b'A', "sound alarm", None, None),  # todo - should alarm have a response?
        request_def(b'a', "silence alarm", None, None),
        request_def(b'c', "fetch constants", None, b'C'),
        request_def(b'd', "define devices", JSONFormat.instance, b'D'),
        request_def(b'E', "erase eeprom", None, None),
        request_def(b'l', "fetch lcd display contents", None, b'L'),
        request_def(b'j', "change settings", JSONFormat.instance, None),
        request_def(b'n', "fetch version", None, b'N'),
        request_def(b's', "fetch settings", None, b'S'),
        request_def(b'v', "fetch values", None, b'V'),
        request_def(b'U', "update device", JSONFormat.instance, b'U'),
        request_def(b't', "fetch temperatures", None, b'T'),
        request_def(b'y', "update simulator", JSONFormat.instance, b'Y'),
    )

    responses = defs_as_dict(
        response_def(b'C', "Constants", JSONFormat.instance),
        response_def(b'D', "log message", LogMessageFormat()),
        response_def(b'L', "lcd display contents", LCDDisplayFormat()),
        response_def(b'N', "version info", VersionFormat()),
        response_def(b'S', "Settings", JSONFormat.instance),
        response_def(b'T', "Temperatures", JSONFormat.instance),
        response_def(b'V', "Values", JSONFormat.instance)
    )

    def __init__(self, conduit):
        super().__init__(conduit)

    def lcd_display(self) -> FutureResponse:
        return self.send_request('L')

    def sound_alarm(self) -> FutureValue:
        return self.send_request('A')

    def silence_alarm(self) -> FutureValue:
        return self.send_request('a')

    def request_temperatures(self) -> FutureValue:
        return self.send_request('t')

    def update_values_json(self, values) -> FutureValue:
        return self.send_request('j', values)

    def send_request(self, request_type, value=None):
        request_type = tobytes(request_type)
        request_defn = self.requests.get(request_type)
        if request_defn is None:
            raise ValueError("unknown command %s" % request_type)
        r = MessageRequest(request_defn, value)
        future = self.async_request(r)
        if request_defn.responses is None:
            # for commands that have no response, set the result value as none immediately
            self._set_future_response(future, None)
        return future

    def _decode_response(self) -> Response:
        reader = self._conduit.input
        char = reader.read(1)
        defn = self.responses.get(char, None)
        if defn is None:
            #log.error("Unrecognized command", char)
            return None

        r = MessageResponse(defn)
        r.from_stream(reader)
        return r

    def __str__(self):
        return "v0.2.4"