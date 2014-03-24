from conduit.base import Conduit
from protocol.async import UnknownProtocolError
from protocol.v02x import brewpi_v02x_protocol_sniffer
from protocol.v03x import brewpi_v03x_protocol_sniffer

__author__ = 'mat'

all_sniffers = [brewpi_v03x_protocol_sniffer, brewpi_v02x_protocol_sniffer]


def determine_protocol(conduit: Conduit):
    # at present all protocols are line based
    l = conduit.input.readline()
    line = l.decode('utf-8')
    error = None
    for sniffer in all_sniffers:
        try:
            p = sniffer(line, conduit)
            if p:
                return p
        except ValueError as e:
            error = e
            break
    raise UnknownProtocolError("unable to determine version from '%s'" % l) from error
