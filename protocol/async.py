"""
The original and ng brewpi protocols are asynchronous. They are represented abstractly as two message queues.
"""
from abc import abstractmethod
from collections import defaultdict, Callable
from concurrent.futures import Future
from io import IOBase
from conduit.base import Conduit

import logging
import threading
import types

logger = logging.getLogger(__name__)


class UnknownProtocolError(Exception):
    pass


def tobytes(arg):
    """
    >>> tobytes("abc")
    b'abc'
    """
    if isinstance(arg, type("")):
        # noinspection PyArgumentList
        arg = bytes(arg, encoding='ascii')
    return arg


class FutureValue(Future):
    """ describes a value that may have not yet been computed. Callers can check if the value has arrived, or chose to
        wait until the value has arrived.
        If an exception is encountered computing the value, it is set."""

    def __init__(self):
        super().__init__()
        self.value_extractor = lambda x: x

    def value(self, timeout=None):
        """ allows the provider to set the result value but provide a different (derived) value to callers. """
        value = self.value_extractor(self.result(timeout))
        if isinstance(value, BaseException):
            raise value
        return value


class Request:
    """ encapsulates the request data. """

    @abstractmethod
    def to_stream(self, file: IOBase):
        """ Encodes the request as bytes in a stream.
        :param file: the file-like instance to stream this request to.
        """
        raise NotImplementedError

    @property
    def response_keys(self):
        """ retrieves an iterable over keys that are used to correlate requests with corresponding responses. """
        raise NotImplementedError
        # todo - maybe just use simple iteration looking for a matching
        # response?


class Response:
    """ Represents a response from a controller method.
    """

    @abstractmethod
    def from_stream(self, file):
        """
        :return: returns the response decoded from the stream. This may be a distinct instance in cases
            where this response is being used as a factory.
        :rtype:Response
        """
        raise NotImplementedError

    @property
    def response_key(self):
        """
        :return: a key that can be used to pair this response with a previous request.
        """
        raise NotImplementedError

    @property
    def value(self):
        raise NotImplementedError


class FutureResponse(FutureValue):
    """ Relates a request and it's future response."""

    def __init__(self, request: Request):
        super().__init__()
        self._request = request
        self.value_extractor = lambda r: r.value

    @property
    def request(self):
        return self._request

    @property
    def response(self):
        """ blocking fetch of the response. """
        return self.result()

    @response.setter
    def response(self, value: Response):
        """
        Sets the successful completion of this future result.
        :param value: The response associated with this future's request.
        """
        self.set_result(value)


class ResponseSupport(Response):
    """ Provides a simple implementation for the value attribute, and request_key.
    """

    def __init__(self, request_key=None, value=None):
        self._request_key = request_key
        self._value = value

    def from_stream(self, file):
        return self

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        """
        :param value:   The new value to assign the value of this response.
        """
        self._value = value

    @property
    def response_key(self):
        return self._request_key


class AsyncHandler:
    """ continually runs a given function. exceptions are logged and posted to a given handler """

    def __init__(self, fn: Callable, args=()):
        self.exception_handler = lambda x: logger.exception(x)
        self.fn = fn
        self.args = args
        self.stop_event = None
        self.background_thread = None

    def start(self):
        if self.background_thread is None:
            t = threading.Thread(target=self._loop, args=self.args)
            t.setDaemon(True)
            self.stop_event = threading.Event()
            self.background_thread = t
            t.start()

    def _loop(self):
        stop = self.stop_event
        while not stop.is_set():
            try:
                self.fn(*self.args)
            except Exception as e:
                self.exception_handler(e)
        logger.info("background thread exiting")

    def stop(self):
        self.stop_event.set()
        if self.background_thread and not self.background_thread is threading.current_thread():
            self.background_thread.join()
        self.background_thread = None


class BaseAsyncProtocolHandler:
    """
    Wraps a conduit in an asynchronous request/response handler. The format for the requests and responses is not defined
    at this level, but the class takes care of registering requests sent along with a future response and associating
    incoming responses with the originating request.

    The primary method to use is async_request(r:Request) which asynchronously sends the request and fetches the
    response. The returned FutureResponse can be used by the caller to check if the response has arrived or wait
    for the response.

    To handle asynchornous responses (with no originating request), use add_unmatched_response_handler(). Subclasses
    may instead provide their own asynchronous handler methods that conform to the expected protocol.
    """

    def __init__(self, conduit: Conduit, matcher=None):
        self._conduit = conduit
        self._requests = defaultdict(list)
        self._unmatched = []
        self.async_thread = None
        if matcher:
            self._matching_futures = types.MethodType(
                matcher, self, BaseAsyncProtocolHandler)

    def start_background_thread(self):
        if self.async_thread is None:
            self.async_thread = AsyncHandler(self.read_response_async)
            self.async_thread.start()

    def stop_background_thread(self):
        if self.async_thread is not None:
            self.async_thread.stop()
            self.async_thread = None

    def add_unmatched_response_handler(self, fn):
        """
        :param fn: A callable that takes a single argument. This function is called with any responses that did not
                originate from a request (such as logs, events and autonomous actions.)
        """
        if not fn in self._unmatched:
            self._unmatched.append(fn)

    def remove_unmatched_response_handler(self, fn):
        self._unmatched.remove(fn)

    def async_request(self, request: Request) -> FutureResponse:
        """ Asynchronously sends a request request to the conduit.
        :param request: The request to send.
        :return: A FutureResponse where the corresponding response to the request can be retrieved when it arrives.
        """
        future = FutureResponse(request)
        self._register_future(future)
        self._stream_request(request)
        return future

    def _stream_request(self, request):
        """ arranges for the request to be streamed. This implementation is synchronous, but subclasses may choose
            to send the request asynchronously. """
        request.to_stream(self._conduit.output)
        # self._conduit.output.flush()
        self._stream_request_sent(request)

    def _register_future(self, future: FutureResponse):
        request = future.request
        if request.response_keys:
            for key in request.response_keys:
                l = self._requests[key]
                l.append(future)
                # todo - handle cancelled/timedout etc.. or otherwise unclaimed FutureResponse objects in
                # would really like weak referencing here.

    def _unregister_future(self, future: FutureResponse):
        request = future.request
        if request.response_keys:
            for key in request.response_keys:
                self._requests.get(key).remove(future)

    @abstractmethod
    def _decode_response(self) -> Response:
        """ reads the next response from the conduit. """
        raise NotImplementedError

    def read_response_async(self):
        if not self._conduit.open:
            self.async_thread.stop()
            return None
        else:
            return self.read_response()

    def read_response(self):
        """ reads the next response from the conduit and processes it. """
        response = self._decode_response()
        return self.process_response(response)

    def process_response(self, response: Response) -> Response:
        if response is not None:
            futures = self._matching_futures(response)
            if futures:
                for f in futures:
                    self._set_future_response(f, response)
            else:
                for callback in self._unmatched:
                    callback(response)
        return response

    def _set_future_response(self, future: FutureResponse, response):
        """ sets the response on the given future and removes the associated request, now that it has been handled. """
        future.response = response
        self._unregister_future(future)

    def _matching_futures(self, response):
        """ finds matching futures for the given response """
        return self._requests.get(response.response_key)

    def _stream_request_sent(self, request):
        """ template method for subclasses to handle when a request has been sent """
        pass
