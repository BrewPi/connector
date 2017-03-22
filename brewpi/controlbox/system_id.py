from controlbox.stateful.controller import WritableObject


class SystemID(WritableObject):
    """ represents the unique ID for the controller that is stored on the controller.
        This is stored as a single byte buffer. """

    def __init__(self):
        super().__init__()

    # todo - this is most likely read only, how to convey that both in the python layer,
    # and in the protocol?
    # at the very least attempting to write to the object will return a error result
