import re
from serial.tools import list_ports
from connector import base
import serial


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


def serial_ports():
    """
    Returns a generator for all available serial ports
    """
    for port in list_ports.comports():
        yield port[0]


def serial_connector_factory(*args, **kwargs) -> base.Conduit:
    """
    Creates a factory function that connects via the serial port.
    All arguments are passed directly to `serial.Serial`
    :return: a factory for serial connectors
    """

    def open_serial_connector():
        ser = serial.Serial(*args, **kwargs)
        return SerialConduit(ser)

    return open_serial_connector


known_devices = {
    (r"%mega2560\.name%.*",r"USB VID\:PID=2341\:0010.*"): "Arduino Mega2560",
    (r"Arduino.*Leonardo.*",r"USB VID\:PID=2341\:8036.*"): "Arduino Leonardo",
    (r"Spark Core.*Arduino.*",r"USB VID\:PID=1D50\:607D.*"): "Spark Core"
}

def matches(text, regex):
    return re.match(regex, text)

def find_arduino_ports(ports):
    for p in ports:
        port, name, desc = p
        for d in known_devices.keys():
            if matches(name, d[0]) and matches(desc, d[1]):
                yield port

def detect_port(port):
    if port == "auto":
        all_ports = tuple(list_ports.comports())
        ports = tuple(find_arduino_ports(all_ports))
        if not ports:
            raise ValueError("Could not find arduino-compatible device in available ports. %s" % repr(all_ports))
        return ports[0]
    return port

