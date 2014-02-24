from abc import abstractmethod
from io import IOBase, RawIOBase

__author__ = 'mat'


class Conduit:
    """
    A conduit allows two-way communication.
    """

    @property
    @abstractmethod
    def input(self) -> RawIOBase:
        """ fetches the I/O stream that provides input.
            Callers can use the usual readXXX() methods. """
        pass

    @property
    @abstractmethod
    def output(self) -> RawIOBase:
        """ fetches the I/O stream that provides output.
            Callers can use the usual writeXXX() methods. """
        pass

    @property
    @abstractmethod
    def open(self) -> bool:
        """ determiens if this conduit is open. When open, the streams provided by
            input and output can be read from/written to."""
        pass

    @abstractmethod
    def close(self):
        """
        Closes both the input and output streams.
        """
        pass


class ConduitDecorator(Conduit):
    def close(self):
        super().close()

    def input(self) -> RawIOBase:
        return super().input

    def open(self) -> bool:
        return super().open

    def output(self) -> RawIOBase:
        return super().output

    def __init__(self, decorate:Conduit):
        self.decorate = decorate


class DefaultConduit(Conduit):
    """ provides the conduit streams from specific read/write file-like types (which may be the same value) """

    def __init__(self, read: RawIOBase=None, write: RawIOBase=None):
        self._read = read
        self._write = write if write is not None else read

    def set_streams(self, read: RawIOBase, write: RawIOBase=None):
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
    def input(self) -> RawIOBase:
        return self._read

    @property
    def output(self) -> RawIOBase:
        return self._write