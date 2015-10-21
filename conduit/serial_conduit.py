"""
Implements a conduit over a serial port.
"""

from __future__ import absolute_import
import logging
import re
from serial import Serial
from serial.tools import list_ports
from conduit.watchdog import ResourceWatchdog
from connector import base


logger = logging.getLogger(__name__)


class SerialConduit(base.Conduit):

    def __init__(self, ser: Serial):
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
    for port in serial_port_info():
        yield port[0]


def serial_connector_factory(*args, **kwargs) -> base.Conduit:
    """
    Creates a factory function that connects via the serial port.
    All arguments are passed directly to `serial.Serial`
    :return: a factory for serial connectors
    """

    def open_serial_connector():
        ser = Serial(*args, **kwargs)
        return SerialConduit(ser)

    return open_serial_connector


known_devices = {
    (r"%mega2560\.name%.*", r"USB VID\:PID=2341\:0010.*"): "Arduino Mega2560",
    (r"Arduino.*Leonardo.*", r"USB VID\:PID=2341\:8036.*"): "Arduino Leonardo",
    (r'Arduino Uno.*', r'USB VID:PID=2341:0043.*'): "Arduino Uno",
    (r"Spark Core.*Arduino.*", r"USB VID\:PID=1D50\:607D.*"): "Spark Core",
    (r".*Photon.*", r"USB VID\:PID=2d04\:c006.*"): "Particle Photon"
}


def matches(text, regex):
    return re.match(regex, text)


def is_recognised_device(p):
    port, name, desc = p
    for d in known_devices.keys():
        # used to match on name and desc, but under linux only desc is
        # returned, compard
        if matches(desc, d[1]):
            return True         # to name and desc on windows
    return False


def find_arduino_ports(ports):
    for p in ports:
        if is_recognised_device(p):
            yield p[0]


def serial_port_info():
    """
    :return: a tuple of serial port info tuples,
    :rtype:
    """
    return tuple(list_ports.comports())


def detect_port(port):
    if port == "auto":
        all_ports = serial_port_info()
        ports = tuple(find_arduino_ports(all_ports))
        if not ports:
            raise ValueError(
                "Could not find arduino-compatible device in available ports. %s" % repr(all_ports))
        return ports[0]
    return port


def configure_serial_for_device(s, d):
    """ configures the serial connection for the given device.
    :param s the Serial instance to configure
    :param d the device (port, name, details) to configure the serial port
    """
    # for now, all devices connect at 57600 baud with defaults for parity/stop
    # bits etc.
    s.setBaudrate(57600)


class SerialWatchdog(ResourceWatchdog):
    """ Monitors local serial ports for known devices. """

    def check(self):
        """ Re-evaluates the available serial ports. """
        self.update_ports(tuple(serial_port_info()))

    def is_allowed(self, key, device):
        return super().is_allowed(key, device) and is_recognised_device(device)

    def update_ports(self, all_ports):
        """ computes the available serial port/device map from a list of tuples (port, name, desc). """
        available = {p[0]: p for p in all_ports if self.is_allowed(
            p[0], p) and is_recognised_device(p)}
        self.update(available)
