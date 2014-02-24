from protocol.async import BaseAsyncProtocolHandler


def encodeId(idChain)->bytearray:
    """
    Encodes a sequence of integers to the on-wire format.

    >>> list(encodeId([1]))
    [1]

    >>> list(encodeId([1,2,3]))
    [129, 130, 3]

    >>> encodeId([])
    bytearray(b'')

    :return:converts a byte array representing an id chain to the comms format.
    :rtype:
    """
    l = len(idChain)
    result = bytearray(l)
    for x in range(0, l-1):
        result[x] = idChain[x] | 0x80
    if (l>0):
        result[l-1] = idChain[l-1]
    return result


class BrewpiV2Protocol(BaseAsyncProtocolHandler):
    """
    Implements the v2 hex-encoded binary protocol.

    Synchronous functions to send a request and wait for the response.
    Asynchronous functions allow many requests to be sent and the responses fetched asynchronously.

    Separate queues/threads for send/receive. send thread pulls requests from the queue and pushes them to the stream
        and to a "sent" queue.
        receive thread takes requests from the stream and pushes them to the receive queue
        handler thread takes requests from the receive queue and looks up corresponding requests (future) in the sent queue.
        also attaches any annotations
        sets the result on the future.

    for async events with no origin, use a listener that is registered to the protocol
        - for auto log of values
        - for logs that aren't attached to any request

    Top-level future is for the whole process: send request,
    """

    def __init__(self, conduit):
        super().__init__(conduit)

    def readValue(self, id):
        result = self._sendCommand(1, encodeId(id))
        return _buffer(result)

    def writeValue(self, id, buf):
        result = self._sendCommand(2, encodeId(id), len(buf), buf)
        return _buffer(result)

    def createObject(self, object_type, id, data)->bool:
        result = self._sendCommand(3, object_type, encodeId(id), len(data), data)
        return not result[0]

    def deleteObject(self, id)->bool:
        result = self._sendCommand(4, encodeId(id))
        return not result[0]

    def nextSlot(self, id):
        pass


    def _sendCommand(self, *args):
        """
        Sends a command. the command is made up of all the arguments. Either an argument is a simple type, which is converted
            to a byte or it is a list type whose elements are converted to bytes.
        The command is sent synchronously and the result is returned. The command may timeout.
        :param args:
        :type args:
        :return:
        :rtype:
        """
        pass


    """
    All commands sent are stored in a queue, along with async callable.
    Responses are used to look up the original command, and the async callable is called with the command result.

    """

class IdChain:
    pass;

class BrewpiV2Request :
    def __init__(self, commandId):
        pass

