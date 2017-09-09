from brewpi.controlbox.codecs.onewire import namedtuple_with_defaults, OneWireBusCodec, OneWireTempSensorCodec, \
    OneWireTempSensorConfigCodec
from brewpi.controlbox.codecs.time import ScaledTimeCodec
from controlbox.stateless.codecs import DictionaryMappingCodecRepo, IdentityCodec

ConnectorType = namedtuple_with_defaults('ConnectorType', ['id', 'state', 'config'])


def _state_codecs(all):
    map = {(type.id, type.state) for type in all if type.state is not None}
    return DictionaryMappingCodecRepo(dict(map))


def _config_codecs(all):
    map = {type.id: type.config for type in all if type.config is not None}
    return DictionaryMappingCodecRepo(dict(map))


class ConnectorTypes():
    """This describes the application types defined in the brewpi controller"""
    # todo - all applications need this so push down into cbconnect-py
    device_id = ConnectorType(0, IdentityCodec, None)
    scaled_time = ConnectorType(1, ScaledTimeCodec, None)
    one_wire_bus = ConnectorType(6, OneWireBusCodec, None)
    one_wire_temp_sensor = ConnectorType(7, OneWireTempSensorCodec, OneWireTempSensorConfigCodec)

    all = [device_id, scaled_time, one_wire_bus, one_wire_temp_sensor]

    _cached_state_repo = _state_codecs(all)
    _cached_config_repo = _config_codecs(all)

    @classmethod
    def state_codecs(cls):
        return cls._cached_state_repo

    @classmethod
    def config_codecs(cls):
        return cls._cached_config_repo


class ConnectorSystemContainer:
    """A mapping of id to object type for objects pre-instantiated by the application in the system container.
    """
    items = [
        ([0], ConnectorTypes.device_id),
        ([1], ConnectorTypes.scaled_time),
        ([2], ConnectorTypes.one_wire_bus)
    ]
