import os
from serial import Serial, SerialException
from conduit.base import Conduit
from conduit.serial import SerialConduit, serial_ports
from connector.base import AbstractConnector

__author__ = 'mat'


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