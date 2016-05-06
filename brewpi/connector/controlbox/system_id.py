
from controlbox.controller import ReadWriteSystemObject, BufferDecoder, BufferEncoder


class SystemID(ReadWriteSystemObject, BufferDecoder, BufferEncoder):
    """ represents the unique ID for the controller that is stored on the controller.
        This is stored as a single byte buffer. """

    def __init__(self, controller, container, slot, length):
        super().__init__(controller, container, slot)
        self.length = length

    def encoded_len(self):
        return self.length
