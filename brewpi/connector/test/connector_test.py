import logging
import os
import sys
from time import sleep

from brewpi.connector.controlbox.objects import MixinController
from brewpi.protocol.factory import all_sniffers
from controlbox.config.config import configure_module
from controlbox.connector.socketconn import TCPServerEndpoint
from controlbox.connector_facade import ControllerDiscoveryFacade
from controlbox.controller import Controlbox, LongDecoder, ShortDecoder
from controlbox.events import ControlboxEvents, ConnectorCodec, ConnectorEventVisitor
from controlbox.protocol.controlbox import ControlboxProtocolV1
from controlbox.protocol.io import determine_line_protocol
from controlbox.support.mixins import StringerMixin, CommonEqualityMixin

logger = logging.getLogger(__name__)

cross_platform_executable = None
configure_module(sys.modules[__name__])


def dump_device_info_typed_controller(connector, protocol: ControlboxProtocolV1):
    if not hasattr(protocol, 'controller'):
        # this was using the typed API - we are using the event API for brewpi
        controller = protocol.controller = MixinController(connector)
        controller.initialize(True)
    else:
        controller = protocol.controller
    id = controller.system_id().read()
    time = controller.system_time().read()
    endpoint = connector.endpoint
    str_id = ''.join('{:02x}'.format(x) for x in id)
    logger.info("device at '%s' id '%s' current time %s " % (endpoint, str_id, time))


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


class BrewpiEvents(ConnectorEventVisitor):
    def __call__(self, event):
        logger.info(event)


def dump_device_info_events(connector, protocol: ControlboxProtocolV1):
    if not hasattr(protocol, 'controller'):
        controller = protocol.controller = Controlbox(connector)
        events = controller.events = ControlboxEvents(controller, BrewpiConstructorCodec(), BrewpiStateCodec())
        events.listeners.add(BrewpiEvents())
    else:
        events = protocol.controller.events

    # todo - would be good if the system itself described the type as part of the read response
    # this makes the system more self-describing
    events.read_system([0], 0)
    events.read_system([1], 1)


def monitor():
    """ logs the connected devices. A dummy protocol sniffer is used. """
    root = logging.getLogger()
    root.addHandler(logging.StreamHandler())
    root.setLevel(logging.INFO)
    builder = ControllerDiscoveryFacade
    logger.info("starting tester")

    def sniffer(conduit):
        return determine_line_protocol(conduit, all_sniffers)

    def handle_connections(managed_connections):
        for c in managed_connections:
            try:
                connector = c.connector
                if connector.connected:
                    dump_device_info_events(connector, connector.protocol)

            except Exception as e:
                logger.exception(e)
                pass

    discoveries = [
        builder.build_serial_discovery(sniffer),
        builder.build_tcp_server_discovery(sniffer, "brewpi", (TCPServerEndpoint('localhost', '127.0.0.1', 8332),))
    ]

    if cross_platform_executable:
        logging.root.info("watching cross platform executable at %s", cross_platform_executable)
        discoveries.append(
            builder.build_process_discovery(sniffer,
                                            cross_platform_executable, "-i 112233445566778899AABBCC".split(" "),
                                            os.path.dirname(cross_platform_executable)))
    facade = builder(discoveries)
    try:
        while True:
            # detect any new connections
            facade.update()
            handle_connections(facade.manager.connections.values())
            sleep(1)
    finally:
        logger.error("exiting main loop")

if __name__ == '__main__':
    monitor()
