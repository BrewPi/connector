
from brewpi.protocol.v02x import brewpi_v02x_protocol_sniffer
from brewpi.protocol.version import VersionParser
from controlbox.protocol.controlbox import ControlboxProtocolV1, \
    build_chunked_hexencoded_conduit


def brewpi_v03x_protocol_sniffer(line, conduit):
    """
    """
    result = None
    line = line.strip()
    if line.startswith("[") and line.endswith("]"):
        info = VersionParser("{" + line[1:-1] + "}")
        if info.major == 0 and info.minor == 3:
            if info.revision == 0:
                result = ControlboxProtocolV1(*build_chunked_hexencoded_conduit(conduit))
    return result


all_sniffers = [brewpi_v03x_protocol_sniffer, brewpi_v02x_protocol_sniffer]
