"""
This is where codecs about the testing scenario (a simple clock that ticks)
lie.
"""

from controlbox.events import ConnectorCodec
from controlbox.support.mixins import StringerMixin, CommonEqualityMixin

class BlockBufferCodec(ConnectorCodec):
    def encode(self, type, value):
        return value

    def decode(self, type, data, mask=None):
        return data


class TypeMappingCodec(ConnectorCodec):
    def __init__(self, codecs: callable):
        self.codecs = codecs

    def encode(self, type, value):
        delegate = self.codecs(type)
        return delegate.encode(type, value)

    def decode(self, type, data, mask=None):
        delegate = self.codecs(type)
        return delegate.decode(type, data, mask)


class DictionaryMappingCodec(TypeMappingCodec):
    def __init__(self, codecs: dict):
        def lookup(type):
            return codecs.get(type)
        super().__init__(lookup)


class BaseState(CommonEqualityMixin, StringerMixin):
    pass


class ScaledTime(BaseState):
    def __init__(self, time, scale):
        self.time = time
        self.scale = scale


class ScaledTimeCodec(ConnectorCodec):
    def decode(self, type, data, mask=None):
        time = LongDecoder()._decode(data[0:4])
        scale = ShortDecoder()._decode(data[4:6])
        return ScaledTime(time, scale)


class BrewpiStateCodec(DictionaryMappingCodec):
    def __init__(self):
        super().__init__({
            0: BlockBufferCodec(),
            1: ScaledTimeCodec()
        })


class BrewpiConstructorCodec(DictionaryMappingCodec):
    def __init__(self):
        super().__init__(dict())
