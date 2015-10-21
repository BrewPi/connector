import operator

from connector.v03x.controller import EmptyDefinition, ReadableObject, UserObject, LongDecoder, ShortDecoder, \
    ShortEncoder, ObjectDefinition, InstantiableObject, CommonEqualityMixin, UnsignedShortDecoder, ContainedObject, \
    ReadWriteUserObject

__author__ = 'mat'


class CurrentTicks(EmptyDefinition, ReadableObject, UserObject, LongDecoder):
    type_id = 3


class ValueProfileInterpolation:
    """ The types of interpolation the value profile can compute. """
    none = 0
    linear = 1
    smooth = 2
    amoother = 3


class TimeValuePoint(CommonEqualityMixin):

    def __init__(self, time=0, value=0):
        self.time = time
        self.value = value

    def decode(self, buf):
        self.time = UnsignedShortDecoder().decode(buf[0:2])
        self.value = ShortDecoder().decode(buf[2:4])
        return self

    def encode(self):
        buf = bytearray(4)
        buf[0:2] = ShortEncoder().encode(self.time)
        buf[2:4] = ShortEncoder().encode(self.value)
        return buf

    @classmethod
    def sort_by_time(cls):
        return operator.attrgetter('time')


class ValueProfileState(ObjectDefinition, CommonEqualityMixin):
    """ Encapsulates the configuration state for a value profile on the controller"""

    def __init__(self):
        """ The current step index in the profile """
        self.current_step = 0
        """ the current time offset in seconds. Can be fractional. """
        self.current_time_offset = 0
        """ When true, the profile continues updating. When false, the profile holds the current value. """
        self.running = False
        """ How values are interpolated between defined points for increased resolution and smooth transitions. """
        self.interpolation = ValueProfileInterpolation.none
        """ The steps of the profile, as a sequence of TimeValuePoint instances.
            There is no implied order to this list. """
        self.steps = []

    def __str__(self):
        return super().__str__() + ":" + str(self.__dict__)

    @classmethod
    def decode_definition(cls, data_block, controller):
        result = ValueProfileState()
        result.decode(data_block)
        return result

    @classmethod
    def encode_definition(cls, arg):
        return arg.encode()

    def decode(self, buf):
        state = buf[0]
        self.current_step = state >> 4 & 0xF
        self.running = state & 4 != 0
        self.interpolation = state & 3
        self.current_time_offset = UnsignedShortDecoder().decode(buf[1:3])
        steps = []
        for i in range(3, len(buf), 4):
            steps.append(TimeValuePoint().decode(buf[i:i + 4]))
        self.steps = steps

    def encode(self):
        buf = bytearray(self.encoded_len())
        buf[0] = (self.current_step << 4) | (
            0 if not self.running else 4) | (self.interpolation & 3)
        buf[1:3] = ShortEncoder().encode(self.current_time_offset)
        self.steps.sort(key=TimeValuePoint.sort_by_time())
        i = 3
        for s in self.steps:
            buf[i:i + 4] = s.encode()
            i += 4
        return buf

    def encoded_len(self):
        return 1 + 2 + len(self.steps) * 4


class ValueProfile(ReadWriteUserObject):
    type_id = 6

    @classmethod
    def encode_definition(cls, args) -> bytes:
        return ValueProfileState.encode_definition(args)

    @classmethod
    def decode_definition(cls, data_block: bytes, controller, *args, **kwargs):
        return ValueProfileState.decode_definition(data_block, controller)
