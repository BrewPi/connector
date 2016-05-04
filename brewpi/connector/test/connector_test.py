import logging

from brewpi.protocol.factory import all_sniffers
from controlbox.connector_facade import ControllerDiscoveryFacade
from controlbox.protocol.io import determine_line_protocol

logger = logging.getLogger(__name__)


def monitor():
    """ logs the connected devices. A dummy protocol sniffer is used. """
    logging.root.setLevel(logging.INFO)
    logging.root.addHandler(logging.StreamHandler())
    builder = ControllerDiscoveryFacade

    def sniffer(conduit):
        return determine_line_protocol(conduit, all_sniffers)

    def handle_connections(connectors):
        for c in connectors:
            try:
                conduit = c.connector.conduit
                if conduit and conduit.open:
                    conduit.input.read()
                    conduit.output.write(b"[]\n")
                    conduit.output.flush()
            except Exception as e:
                logger.exception(e)
                pass

    discoveries = (builder.build_serial_discovery(sniffer),
                   builder.build_tcp_server_discovery(sniffer, "brewpi"))
    facade = builder(discoveries)
    while True:
        # detect any new
        facade.update()
        handle_connections(facade.manager.connections.values())

if __name__ == '__main__':
    monitor()
