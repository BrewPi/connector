import os
from serial import Serial, SerialException
from serial.tools import list_ports
from conduit.base import Conduit
from conduit.serial import SerialConduit
from connector.base import Connector, AbstractConnector, ConnectionNotAvailableError

__author__ = 'mat'


def serial_ports():
    """
    Returns a generator for all available serial ports
    """
    for port in list_ports.comports():
        yield port[0]


class SerialConnector(AbstractConnector):
    def __init__(self, serial:Serial):
        """
        Creates a new serial connector.
        :param serial - the serial object defining the serial port to connect to.
                The serial instance should not be open.
        """
        super().__init__()
        self._serial = serial
        if serial.isOpen():
            raise ValueError

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
            except SerialException as e:
                raise ConnectionError from e

    def _connect(self)->Conduit:
        self._try_open()
        conduit = SerialConduit(self._serial)
        self._protocol = self._establish_protocol()
        return conduit

    def _disconnect(self):
        self._serial.close()
        pass

    def _try_available(self):
        n = self._serial.name
        try:
            return n in serial_ports()
        except SerialException:
            return False