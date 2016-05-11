import logging
import os
from time import sleep

from brewpi.connector.controlbox.objects import MixinController
from brewpi.protocol.factory import all_sniffers
from controlbox.connector_facade import ControllerDiscoveryFacade
from controlbox.protocol.controlbox import ControlboxProtocolV1
from controlbox.protocol.io import determine_line_protocol

logger = logging.getLogger(__name__)


cross_platform_executable = "/Users/mat1/dev/brewpi/firmware/platform/spark/target/cbox-gcc/cbox"


def dump_device_info(connector, protocol: ControlboxProtocolV1):
    if not hasattr(protocol, 'controller'):
        controller = protocol.controller = MixinController(connector)
        controller.initialize(True)
    else:
        controller = protocol.controller
    id = controller.system_id().read()
    time = controller.system_time().read()
    endpoint = connector.endpoint
    str_id = ''.join('{:02x}'.format(x) for x in id)
    logger.info("device at '%s' id '%s' current time %s " % (endpoint, str_id, time))


def monitor():
    """ logs the connected devices. A dummy protocol sniffer is used. """
    logging.root.setLevel(logging.INFO)
    logging.root.addHandler(logging.StreamHandler())
    builder = ControllerDiscoveryFacade

    def sniffer(conduit):
        return determine_line_protocol(conduit, all_sniffers)

    def handle_connections(managed_connections):
        for c in managed_connections:
            try:
                connector = c.connector
                if connector.connected:
                    dump_device_info(connector, connector.protocol)

            except Exception as e:
                logger.exception(e)
                pass

    discoveries = (
        builder.build_serial_discovery(sniffer),
        builder.build_tcp_server_discovery(sniffer, "brewpi"),
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
