from brewpi.controlbox import OneWireBusCodec, OneWireTempSensorCodec, OneWireTempSensorConfigCodec, \
    namedtuple_with_defaults
from brewpi.controlbox import ScaledTimeCodec
from controlbox.stateless.codecs import DictionaryMappingCodec, IdentityCodec

ConnectorType = namedtuple_with_defaults('ConnectorType', ['id', 'state', 'config'])


class ConnectorTypes():
    device_id = ConnectorType(0, IdentityCodec, None)
    scaled_time = ConnectorType(1, ScaledTimeCodec, None)
    one_wire_bus = ConnectorType(6, OneWireBusCodec, None)
    one_wire_temp_sensor = ConnectorType(7,  OneWireTempSensorCodec,  OneWireTempSensorConfigCodec)

    all = [device_id, scaled_time, one_wire_bus, one_wire_temp_sensor]

    def state_codec(self):
        map = { (type.id, type.state) for type in self.all if type.state is not None }
        return DictionaryMappingCodec(dict(map))

    def config_codec(self):
        map = { type.id:type.config for type in self.all if type.config is not None }
        return DictionaryMappingCodec(dict(map))


class ConnectorSystemContainer:
    items = dict([
        ([0], ConnectorTypes.device_id),
        ([1], ConnectorTypes.scaled_time),
        ([2], ConnectorTypes.one_wire_bus),
    ])


