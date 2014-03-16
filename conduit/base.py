from abc import abstractmethod
from io import IOBase, RawIOBase, BufferedIOBase
import io

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
        self.decorate.close()

    @property
    def input(self) -> IOBase:
        return self.decorate.input

    @property
    def output(self) -> IOBase:
        return self.decorate.output

    @property
    def open(self) -> bool:
        return self.decorate.open

    def __init__(self, decorate: Conduit):
        self.decorate = decorate


def close_stream(stream):
    if stream is not None:
        stream.close()


class ConduitStreamDecorator(ConduitDecorator):
    """ provides a simple way to wrap the input and output streams from a conduit."""

    def __init__(self, decorate: Conduit):
        super().__init__(decorate)
        self._input = None
        self._output = None

    @property
    def input(self) -> IOBase:
        if self._input is None:
            self._input = self._wrap_input(self.decorate.input)
        return self._input

    @property
    def output(self) -> IOBase:
        if self._output is None:
            self._output = self._wrap_output(self.decorate.output)
        return self._output

    def close(self):
        self._output.flush()
        super().close()

    @abstractmethod
    def _wrap_input(self, input):
        return input

    @abstractmethod
    def _wrap_output(self, output):
        return output


class BufferedConduit(ConduitStreamDecorator):
    """ buffers the underlying streams from the given conduit."""
    def _wrap_output(self, output):
        return io.BufferedWriter(output)

    def _wrap_input(self, input):
        return io.BufferedReader(input)


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