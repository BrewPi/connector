
from controlbox.controller import ReadWriteSystemObject, BufferDecoder, BufferEncoder


class SystemID(ReadWriteSystemObject, BufferDecoder, BufferEncoder):
    """ represents the unique ID for the controller that is stored on the controller.
        This is stored as a single byte buffer. """

    def encoded_len(self):
        return 1
