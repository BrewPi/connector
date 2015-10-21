from concurrent.futures import ThreadPoolExecutor, Future
from queue import Queue, Empty
from abc import abstractmethod
from conduit.base import Conduit

__author__ = 'mat'


class AsyncConnectorTest:
    """
    Provides support for implementing asynchronous tests on connectors.
    """
    connections = None
    futures = None
    executor = None

    def setUp(self):
        self.connections = self.createConnections()
        self.executor = ThreadPoolExecutor(len(self.connections) * 2)

        def connectionQueues(c) -> (Future, Future):
            c.sendQueue = Queue()
            c.receiveQueue = Queue()
            result = (self.executor.submit(self.writeFromQueueToConnection, c.sendQueue, c),
                      self.executor.submit(self.readFromConnectionToQueue, c, c.receiveQueue))
            return result

        self.futures = [
            q for c in self.connections for q in connectionQueues(c)]

    def tearDown(self):
        if self.connections:
            for connection in self.connections:
                connection.close()
        self.executor.shutdown(wait=True)
        for f in self.futures:  # any exceptions thrown will be propagated here
            f.result()

    def readFromConnectionToQueue(self, connector: Conduit, queue: Queue):
        while connector.open:
            queue.put(connector.input.readline())

    def writeFromQueueToConnection(self, queue: Queue, connector: Conduit):
        while connector.open:
            try:
                lines = queue.get(timeout=1)
            except (TimeoutError, Empty):
                pass
            else:
                connector.output.write(lines.encode())

    def assertWriteRead(self, text, connectors):
        for line in text.split('\n'):
            # rather than writing directly to the connector, put it in the send
            # queue
            connectors[0].sendQueue.put(line)
            for c in connectors[1:]:
                read = c.receiveQueue.get()
                self.assertEqual(read, str.encode(line))

    @abstractmethod
    def createConnections(self):
        raise NotImplementedError
