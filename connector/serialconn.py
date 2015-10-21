import logging
from serial import Serial, SerialException
import time
from conduit.base import Conduit
from conduit.serial_conduit import SerialConduit, serial_ports, serial_port_info, SerialWatchdog, \
    configure_serial_for_device
from conduit.watchdog import ResourceAvailableEvent, ResourceUnavailableEvent
from connector.base import AbstractConnector, ConnectorError

__author__ = 'mat'

logger = logging.getLogger(__name__)


class SerialConnector(AbstractConnector):

    def __init__(self, serial: Serial):
        """
        Creates a new serial connector.
        :param serial - the serial object defining the serial port to connect to.
                The serial instance should not be open.
        """
        super().__init__()
        self._serial = serial
        if serial.isOpen():
            raise ValueError("serial object should be initially closed")

    def _connected(self):
        return self._serial.isOpen()

    def _try_open(self):
        """
        :return: True if the serial port is connected.
        :rtype: bool
        """
        s = self._serial
        if not s.isOpen():
            try:
                s.open()
                logger.info("opened serial port %s" % self._serial.port)
                time.sleep(5)
            except SerialException as e:
                logger.error("error opening serial port %s: %s" %
                             self._serial.port, e)
                raise ConnectorError from e

    def _connect(self)->Conduit:
        self._try_open()
        return SerialConduit(self._serial)

    def _disconnect(self):
        self._serial.close()
        pass

    def _try_available(self):
        n = self._serial.name
        try:
            return n in serial_ports()
        except SerialException:
            return False


class SerialConnectorFactory:
    """ The factory used to create a connection
    """

    def __init__(self, port, device):
        s = Serial()
        s.setPort(port)
        configure_serial_for_device(s, device)
        self.serial = s
        self.connector = SerialConnector(s)

    def __enter__(self):
        try:
            logger.debug("Detected device on %s" % self.serial.port)
            self.connector.connect()
            logger.debug("Connected device on %s using protocol %s" %
                         (self.serial.port, self.connector.protocol))
        except ConnectorError as e:
            s = str(e)
            logger.error("Unable to connect to device on %s - %s" %
                         (self.serial.port, s))
            raise e

    def __exit__(self):
        logger.debug("Disconnected device on %s" % self.serial.port)
        self.connector.disconnect()


def log_connection_events(event):
    if isinstance(event, ResourceAvailableEvent):
        logger.info("Detected device on %s" % event.source)
        logger.info("Connected device on %s using protocol %s" %
                    (event.source, event.resource.connector.protocol))
    if isinstance(event, ResourceUnavailableEvent):
        logger.info("Disconnected device on %s" % event.source)


def monitor():
    """ A helper function to monitor serial ports for manual testing. """
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())
    logger.info(serial_port_info())

    w = SerialWatchdog(SerialConnectorFactory)
    w.listeners += log_connection_events
    while True:
        time.sleep(0.5)
        w.check()

if __name__ == '__main__':
    monitor()
