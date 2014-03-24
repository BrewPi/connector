"""
   Attempts to open a given connector via a factory function.
"""

import logging
from support.events import EventHook

logger = logging.getLogger(__name__)


class ResourceEvent:
    """ Notification that a conduit is available. """
    def __init__(self, source, resource):
        self.source = source
        self.resource = resource


class ResourceAvailableEvent(ResourceEvent):
    """ Signifies that a conduit is available. """


class ResourceUnavailableEvent(ResourceEvent):
    """ Signifies that a conduit has become unavailable. """


class ResourceWatchdog:
    """ Monitors serial ports, and posts notification when a new device is available. """
    previous = {}
    connections = {}
    excluded = {}
    listeners = None

    def __init__(self, connection_factory):
        """
        :param connection_factory:  A factory to create a connection from a given (port, device) tuple.
            The connection should support the context manager protocol (See PEP 343)
        :type connection_factory: callable
        """
        self.listeners = EventHook()
        self.factory = connection_factory

    def is_allowed(self, port, device):
        """ @param port: a tuple of (port, name, details) for a device connected to a serial port. """
        return not self.excluded.get(port, None) and not self.excluded.get(device, None)

    def _attach(self, port, device):
        connection = self.factory(port, device)
        try:
            connection.__enter__()
            self.connections[port] = connection
            return connection
        except Exception as e:
            logger.info(e)
            return None

    def _detach(self, port, device):
        conduit = self.connections.get(port, None)
        if conduit:
            try:
                del self.connections[port]
                conduit.__exit__()
            except Exception as e:
                logger.info(e)
        return conduit

    def update(self, available: dict):
        """
        :param available: dictionary of resource location to resource info. The key is a logical name for the
            resource, while the value is a physical attribute.
        :type available: dict
        :return:
        :rtype:
        """
        current_resources = {p: None for p in self.previous}  # union of all previous and current ports
        current_resources.update(available)
        events = []
        for handle,current in current_resources.items():
            previous = self.previous.get(handle, None)
            if current != previous:
                not previous or events.append(ResourceUnavailableEvent(handle, self._detach(handle, previous)))
                not current or events.append(ResourceAvailableEvent(handle, self._attach(handle, current)))
        self.previous = available
        self.listeners.fire_all([e for e in events if e.resource])




