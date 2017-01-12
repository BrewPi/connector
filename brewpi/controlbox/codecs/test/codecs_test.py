from unittest import TestCase

from brewpi.controlbox import ConnectorTypes
from controlbox.stateless.codecs import DictionaryMappingCodec


class ConnectorTypesTest(TestCase):

    def test_can_fetch_config_codec(self):
        sut = ConnectorTypes()
        codec = sut.config_codec()
        self.assertIsInstance(codec, DictionaryMappingCodec)
        actual = codec.lookup(sut.one_wire_temp_sensor.id)
        self.assertEqual(actual, sut.one_wire_temp_sensor.config)
