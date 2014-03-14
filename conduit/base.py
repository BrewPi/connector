from abc import abstractmethod
from io import IOBase, RawIOBase, BufferedIOBase

__author__ = 'mat'


class Conduit:
    """
    A conduit allows two-way communication.
    """

    @property
    @abstractmethod
    def input(self) -> IOBase:
        """ fetches the I/O stream that provides input.
            Callers can use the usual readXXX() methods. """
        raise NotImplementedError

    @property
    @abstractmethod
    def output(self) -> IOBase:
        """ fetches the I/O stream that provides output.
            Callers can use the usual writeXXX() methods. """
        raise NotImplementedError

    @property
    @abstractmethod
    def open(self) -> bool:
        """ determiens if this conduit is open. When open, the streams provided by
            input and output can be read from/written to."""
        raise NotImplementedError

    @abstractmethod
    def close(self):
        """
        Closes both the input and output streams.
        """
        raise NotImplementedError


class ConduitDecorator(Conduit):
    def close(self):
        super().close()

    def input(self) -> IOBase:
        return super().input

    def output(self) -> IOBase:
        return super().output

    def open(self) -> bool:
        return super().open

    def __init__(self, decorate:Conduit):
        self.decorate = decorate


class DefaultConduit(Conduit):
    """ provides the conduit streams from specific read/write file-like types (which may be the same value) """

    def __init__(self, read: BufferedIOBase=None, write: BufferedIOBase=None):
        self._read = read
        self._write = write if write is not None else read

    def set_streams(self, read: BufferedIOBase, write: BufferedIOBase=None):
        self._read = read
        self._write = write if write is not None else read

    def close(self):
        self._write.close()
        self._read.close()

    @property
    def open(self):
        """ toto - check underlying streams, or catch calls to close(). """
        return True

    @property
    def input(self) -> IOBase:
        return self._read

    @property
    def output(self) -> IOBase:
        return self._write