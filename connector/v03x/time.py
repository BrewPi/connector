import operator

from connector.v03x.controller import EmptyDefinition, ReadableObject, UserObject, LongDecoder, ShortDecoder, \
    ShortEncoder

__author__ = 'mat'


class CurrentTicks(EmptyDefinition, ReadableObject, UserObject, LongDecoder):
    type_id = 3


class ValueProfileInterpolation:
    """ The types of interpolation the value profile can compute. """
    none = 0
    linear = 1
    smooth = 2
    amoother = 3


class TimeValuePoint():
    time = 0
    value = 0

    def __init__(self, time, value):
        self.time = time
        self.value = value

    def decode(self, buf):
        self.time = ShortDecoder().decode(buf[0:2])
        self.value = ShortDecoder().decode(buf[2:4])

    def encode(self):
        buf = bytearray(4)
        buf[0:2] = ShortEncoder().encode(self.time)
        buf[2:4] = ShortEncoder().encode(self.value)
        return buf

    @classmethod
    def sort_by_time(cls):
        return operator.attrgetter('time')


class ValueProfileState():
    """ Encapsulates the configuration state for a value profile on the controller"""

    current_step = 0
    """ The current step index in the profile """

    current_time_offset = 0
    """ the current time offset in seconds. Can be fractional. """

    running = False
    """ When true, the profile continues updating. When false, the profile holds the current value. """

    interpolation = ValueProfileInterpolation.none
    """ How values are interpolated between defined points for increased resolution and smooth transitions. """

    steps = None
    """ The steps of the profile, as a sequence of TimeValuePoint instances. There is no implied order to this list. """

    def __init__(self):
        self.steps = []

    def decode(self, buf):
        state = buf[0]
        self.current_step = state >> 4 & 0xF
        self.running = state & 4 != 0
        self.interpolation = state & 3
        self.current_time_offset = ShortDecoder().decode(buf[1:3])

    def encode(self):
        buf = bytearray(self.encoded_len())
        buf[0] = (self.current_step << 4) | (0 if not self.running else 4) | (self.interpolation & 3)
        buf[1:3] = ShortEncoder().encode(self.current_time_offset)
        self.steps.sort(key = TimeValuePoint.sort_by_time())
        i = 3
        for s in self.steps:
            buf[i:i+4] = s.encode()
            i+=4
        return buf

    def encoded_len(self):
        return 1 + 2 + len(self.steps)*4



class ValueProfile(ValueProfileState):
    type_id = 6

