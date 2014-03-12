from io import IOBase, BufferedIOBase
import json
from concurrent.futures import Future
from queue import Queue
from threading import Lock
from abc import abstractmethod
from conduit.base import Conduit
from protocol.async import FutureValue, Request, BaseAsyncProtocolHandler, FutureResponse, Response

__author__ = 'mat'


class AvrInfo:
    """ Parses and stores the version and other compile-time details reported by the Arduino """
    version = "v"
    build = "n"
    simulator = "y"
    board = "b"
    shield = "s"
    log = "l"

    shield_revA = "revA"
    shield_revC = "revC"

    shields = {1: shield_revA, 2: shield_revC}

    board_leonardo = "leonardo"
    board_standard = "standard"
    board_mega = "mega"

    boards = {'l': board_leonardo, 's': board_standard, 'm': board_mega}

    def __init__(self, s=None):
        self.major = 0
        self.minor = 0
        self.revision = 0
        self.version = None
        self.build = 0
        self.simulator = False
        self.board = None
        self.shield = None
        self.log = 0
        self.parse(s)


    def parse(self, s):
        if s is None or len(s) == 0:
            pass
        else:
            s = s.strip()
            if s[0] == '{':
                self.parseJsonVersion(s)
            else:
                self.parseStringVersion(s)

    def parseJsonVersion(self, s):
        j = json.loads(s)
        if AvrInfo.version in j:
            self.parseStringVersion(j[AvrInfo.version])
        if AvrInfo.simulator in j:
            self.simulator = j[AvrInfo.simulator] == 1
        if AvrInfo.board in j:
            self.board = AvrInfo.boards.get(j[AvrInfo.board])
        if AvrInfo.shield in j:
            self.shield = AvrInfo.shields.get(j[AvrInfo.shield])
        if AvrInfo.log in j:
            self.log = j[AvrInfo.log]
        if AvrInfo.build in j:
            self.build = j[AvrInfo.build]

    def parseStringVersion(self, s):
        s = s.strip()
        parts = [int(x) for x in s.split('.')]
        parts += [0] * (3 - len(parts))  # pad to 3
        self.major, self.minor, self.revision = parts[0], parts[1], parts[2]
        self.version = s


class CharacterLCDInfo:
    """ describes an LCD attached to the controller
    """

    def __init__(self, width, height):
        self.width = width
        self.height = height

    @property
    def dimensions(self):
        return (self.width, self.height)


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


def tobytes(arg):
    if type(arg) is type(""):
        arg = bytearray(arg, 'ascii')
    return arg


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
        return AvrInfo(line)

    def produce(self, item, writer):
        raise NotImplementedError


class LCDDisplayFormat(MessageFormat):
    pass


class LogMessageFormat(MessageFormat):
    pass


class BaseDef(object):
    char = None
    name = None
    format = None


class RequestDef(BaseDef):
    responses = None


class ResponseDef(BaseDef):
    pass;


def request_def(char, name, format, responses):
    return make_dynamic(locals(), RequestDef())


def response_def(char, name, format):
    return make_dynamic(locals(), ResponseDef())


def make_dynamic(dict, target):
    for x, y in dict.items():
        setattr(target, x, y)
    return target


def defs_as_dict(*defs):
    """ creates a map from request/response code to the request/response tuple """
    return dict((d.char, d) for d in defs)


class MessageRequest(Request):
    def __init__(self, defn:RequestDef, value=None):
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
        mf = self.defn.format
        value = self.value
        if mf is not None and value is not None:
            mf.produce(value, file)
        file.write(b'\n')


class MessageResponse(Response):
    def __init__(self, defn):
        self.defn = defn
        self._value = None

    def from_stream(self, file):
        if self.defn.format is not None:
            self._value = self.defn.format.scan(file)

    @property
    def response_key(self):
        return self.defn.char

    @property
    def value(self):
        return self._value


class BrewpiProtocolV023(BaseAsyncProtocolHandler):
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

    def lcdDisplay(self) -> FutureResponse:
        return self.send_request('L')

    def soundAlarm(self) -> FutureValue:
        return self.send_request('A')

    def silenceAlarm(self) -> FutureValue:
        return self.send_request('a')

    def requestTemperatures(self) -> FutureValue:
        return self.send_request('t')

    def update_values_json(self, dict) -> FutureValue:
        return self.send_request('j', dict)

    def send_request(self, requestType, value=None):
        if type(requestType) is type(""):
            requestType = bytes(requestType, 'ascii')
        request_defn = self.requests.get(requestType)
        if request_defn is None:
            raise ValueError("unknown command %s" % requestType)
        r = MessageRequest(request_defn, value)
        future = self.async_request(r)
        if request_defn.responses is None:  # for commands that have no response, set the result value as none immediately
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




