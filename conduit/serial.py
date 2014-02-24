import types

__author__ = 'mat'

from . import base
import serial

def serial_connector_factory(*args, **kwargs) -> base.Conduit:
    """
    Creates a factory function that connects via the serial port.
    All arguments are passed directly to `serial.Serial`
    :return: a factory for serial connectors
    """

    class SerialConduit(base.Conduit):

        def __init__(self, ser: serial.Serial):
            self.ser = ser

        @property
        def input(self):
            return self.ser

        @property
        def output(self):
            return self.ser

        @property
        def open(self) -> bool:
            return self.ser.isOpen()

        def close(self):
            self.ser.close()

    def open_serial_connector():
        ser = serial.Serial(*args, **kwargs)
        return SerialConduit(ser)

    return open_serial_connector

