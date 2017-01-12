import collections
from abc import abstractmethod
from decimal import Decimal

from controlbox.stateful.controller import Codec, LongCodec, LongDecoder, ShortCodec, ValueDecoder
from controlbox.stateless.codecs import BaseState, ConnectorCodec


def namedtuple_with_defaults(typename, field_names, default_values=()):
    T = collections.namedtuple(typename, field_names)
    T.__new__.__defaults__ = (None,) * len(T._fields)
    if isinstance(default_values, collections.Mapping):
        prototype = T(**default_values)
    else:
        prototype = T(*default_values)
    T.__new__.__defaults__ = tuple(prototype)
    return T


class OneWireAddress(BaseState):

    length = 8

    def __init__(self, address: bytearray):
        self.address = address

    @staticmethod
    # todo in more recent code, decoding has been separated from the state objects
    def decode_addresses(data):
        addresses = []
        while len(data) >= 8:
            addresses.append(OneWireAddress(data[0:OneWireAddress.length]))
            data = data[OneWireAddress.length:]
        return addresses


OneWireBusRead = namedtuple_with_defaults('OneWireBusRead', ['success', 'addresses'], [None, None])


class OneWireCommandSupport:
    """
        The command object represents the command to invoke on the one wire bus.
        It doesn't directly handle encoding/decoding since these are not aspects we need to provide to
        clients.
    """

    def __init__(self, name):
        self.name = name

    def accept(self, visitor: "OneWireCommand.Visitor"):
        return getattr(visitor, self.name)(self)


class OneWireCommand:
    class Noop(OneWireCommandSupport):
        def __init__(self):
            super().__init__('noop')

    class Reset(OneWireCommandSupport):
        def __init__(self):
            super().__init__('reset')

    class Search(OneWireCommandSupport):
        def __init__(self):
            super().__init__('search')

    class FamilySearch(OneWireCommandSupport):
        def __init__(self, family):
            super().__init__('family_search')
            self.family = family

    all_commands = [ Noop, Reset, Search, FamilySearch ]

    class Visitor:
        @abstractmethod
        def noop(self, noop):
            pass

        @abstractmethod
        def reset(self, reset):
            pass

        @abstractmethod
        def search(self, search):
            pass

        @abstractmethod
        def family_search(self, family):
            pass


class OneWireCommandResult(ConnectorCodec):
    """
    Decodes the response from the OneWireBus object, which is
    the result of the command. The format is currently fixed, and not context sensitive.
    1 byte is the command result (>=0 for success)
    followed by N*8 bytes for the OneWire addresses of the devices found.
    """

    def encode(self, type, value):
        return super().encode(type, value)

    def decode(self, type, data, mask=None):
        success = None
        addresses = None
        length = len(data)
        if length > 0:
            success = data[0] >= 0
            if length > 1:
                addresses = OneWireAddress.decode_addresses(data[1:])
        return OneWireBusRead(success, addresses)


class OneWireCommandsCodec(ConnectorCodec):
    """
    Encodes a OneWireCommand object.
    """

    def decode(self, type, data, mask=None):
        return super().decode(type, data, mask)

    class EncodeVisitor(OneWireCommand.Visitor):

        def noop(self, noop):
            return bytearray([0])

        def reset(self, noop):
            return bytearray([1])

        def search(self, noop):
            return bytearray([2])

        def family_search(self, family:OneWireCommand.FamilySearch):
            return bytearray([3, family.family])

    def __init__(self):
        self.visitor = OneWireCommandsCodec.EncodeVisitor()

    def encode(self, type, value: OneWireCommandSupport):
        return value.accept(self.visitor)


class OneWireBusCodec(ConnectorCodec):

    def __init__(self):
        self.encoder = OneWireCommandsCodec()
        self.deoder = OneWireCommandResult()

    def encode(self, type, value):
        return self.encoder.encode(type, value)

    def decode(self, type, data, mask=None):
        return self.decoder.decode(type, data, mask)


class OneWireTempSensorState(BaseState):

    def __init__(self, connected=None, temperature=None):
        self.connected = connected
        self.temperature = temperature


class LongTempDecoder(LongDecoder):
    """
    Decodes a temp_long_t type from the byte stream
    """
    scale = Decimal(1<<8)

    def _decode(self, buf):
        value = super().decode(buf)
        return Decimal(value)/self.scale


class FixedPointCodec(Codec):
    def __init__(self, codec, scale):
        self.codec = codec
        self.scale = Decimal(scale)

    def encode(self, value):
        return self.codec.encode(value*self.scale)

    def decode(self, data, mask=None):
        return self.codec.decode(data) / self.scale


class TempCodec(FixedPointCodec):
    """
    Decodes a temp_t type from the byte stream
    """
    def __init__(self):
        super().__init__(ShortCodec(), 1<<7)


class LongTempCodec(FixedPointCodec):
    """
    Decodes a temp_t type from the byte stream
    """
    def __init__(self):
        super().__init__(LongCodec(), 1<<8)


class OneWireTempSensorCodec(ConnectorCodec):
    def __init__(self):
        self.long_temp = LongTempCodec()

    def encode(self, type, value):
        return super().encode(type, value)

    def decode(self, type, data, mask=None):
        connected = data[0]!=0
        temperature = self.long_temp.decode(type, data[1:5])
        return OneWireTempSensorState(connected, temperature)


class OneWireTempSensorConfig(BaseState):
    def __init__(self, address=None, offset=None):
        self.address = address
        self.offset = offset


class OneWireAddressDecoder(ValueDecoder):

    def _decode(self, buf):
        return OneWireAddress(buf[0:OneWireAddress.length])

    def encoded_len(self):
        return OneWireAddress.length


class OneWireAddressCodec(Codec):

    decoder = OneWireAddressDecoder()

    def encoded_len(self):
        return OneWireAddress.length

    def encode(self, value:OneWireAddress):
        return bytearray(value.address)

    def decode(self, data, mask=None):
        return self.decoder.decode(data)


class ConnectorCodecAdapter(ConnectorCodec):
    """
    Removes the type parameter and forwards the calls to the
    more basic codec types.
    """
    def __init__(self, codec):
        self.codec = codec

    def encode(self, type, value):
        return self.codec.encode(value)

    def decode(self, type, data, mask=None):
        return self.codec.decode(data)


class OneWireTempSensorConfigCodec(ConnectorCodec):
    address = OneWireAddressCodec()
    offset = TempCodec()

    def encode(self, type, value:OneWireTempSensorConfig):
        address_bytes = self.address.encode(value.address)
        offset_bytes = self.offset.encode(value.offset)
        return address_bytes + offset_bytes

    def decode(self, type, data, mask=None):
        # todo - not sure I like this hard coding of sizes
        address = self.address.decode(data[0:8])
        offset = self.offset.decode(data[8:10])
        return OneWireTempSensorConfig(address, offset)