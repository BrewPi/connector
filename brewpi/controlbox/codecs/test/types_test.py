from unittest import TestCase

from brewpi.controlbox.codecs.types import ConnectorTypes
from controlbox.stateless.codecs import DictionaryMappingCodecRepo


class ConnectorTypesTest(TestCase):

    def test_can_fetch_config_codecs(self):
        sut = ConnectorTypes()
        codec = sut.config_codecs()
        self.assertIsInstance(codec, DictionaryMappingCodecRepo)
        actual = codec.lookup(ConnectorTypes.one_wire_temp_sensor.id)
        self.assertEqual(actual, sut.one_wire_temp_sensor.config)

    # todo - fix this
    # def test_can_fetch_state_codecs(self):
    #     sut = ConnectorTypes()
    #     codec = sut.state_codecs()
    #     self.assertIsInstance(codec, DictionaryMappingCodecRepo)
    #     actual = codec.lookup(ConnectorTypes.one_wire_temp_sensor.id)
    #     self.assertEqual(actual, sut.one_wire_temp_sensor.config)
