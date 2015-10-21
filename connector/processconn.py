import logging
import os
from conduit.base import Conduit, BufferedConduit
from conduit.process_conduit import ProcessConduit
from connector.base import AbstractConnector, ConnectorError

__author__ = 'mat'

logger = logging.getLogger(__name__)


def is_executable(file):
    return os.path.isfile(file) and os.access(file, os.X_OK)


class ProcessConnector(AbstractConnector):
    """ Instantiates a process and connects to it via standard in/out. """

    def __init__(self, image, args=None):
        super().__init__()
        self.image = image
        self.args = args
        self.build_conduit = lambda x: x

    def _connected(self):
        return self._conduit.open

    def _disconnect(self):
        pass

    def _connect(self) -> Conduit:
        try:
            args = self.args if self.args is not None else []
            p = ProcessConduit(self.image, *args)
            return p
        except (OSError, ValueError) as e:
            logger.error(e)
            raise ConnectorError from e

    def _try_available(self):
        return is_executable(self.image)
