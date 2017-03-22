"""
Codecs provide the knowledge of how to transform between a buffer of bytes and a higher-level representation.
Codecs provide an encode
"""

from controlbox.stateless.codecs import BaseState, ShortDecoder, LongDecoder, Codec


class ScaledTime(BaseState):
    def __init__(self, time, scale):
        self.time = time
        self.scale = scale


class ScaledTimeCodec(Codec):
    def decode(self, type, data, mask=None):
        time = LongDecoder()._decode(data[0:4])
        scale = ShortDecoder()._decode(data[4:6])
        return ScaledTime(time, scale)
