from connector.v03x.controller import *
from connector.v03x.time import CurrentTicks, ValueProfile
from protocol.v03x import decode_id, encode_id

__author__ = 'mat'


# Now comes the application-specific objects.

class PersistentValueBase(EncoderDecoderDefinition, ReadWriteValue, ForwardingEncoder, ForwardingDecoder):
    """ This is split into a base class to support system and user persisted values. The default value type is
        a buffer. This can be changed by setting the encoder and decoder attributes. """
    decoder = BufferDecoder()
    encoder = BufferEncoder()

    def encoded_len(self):
        return 0  # not known


class PersistentValue(PersistentValueBase, ReadWriteUserObject):
    """ A user persistent value. """
    type_id = 5

    def write_mask(self, value, mask):
        """ Allows a partial update of the value via a masked write. Wherever the mask bit has is set, the corresponding
            bit from value is written.
        """
        return self.controller.write_masked_value(self, (value, mask))


class PersistentShortValue(PersistentValue):
    decoder = ShortDecoder()
    encoder = ShortEncoder()


class LogicActuator:
    type_id = 7


class BangBangController:
    type_id = 8


class PersistChangeValue(ReadWriteUserObject, ShortEncoder, ShortDecoder, ReadWriteValue):
    """ A persistent value in the controller. The value is persisted when it the amount it changes from the last persisted
    value passes a certain threshold.
    Definition args: a tuple of (initial value:signed 16-bit, threshold: unsigned 16-bit). """
    type_id = 9
    shortEnc = ShortEncoder()
    shortDec = ShortDecoder()

    @classmethod
    def encode_definition(cls, arg):
        if arg[1] < 0:
            raise ValueError("threshold < 0")
        return cls.shortEnc.encode(arg[0]) + cls.shortEnc.encode(arg[1])

    @classmethod
    def decode_definition(cls, data_block: bytes, *args, **kwargs):
        return cls.shortDec.decode(data_block[0:2]), cls.shortDec.decode(data_block[2:4])


class IndirectValue(ReadWriteUserObject):
    type_id = 0x0D

    @classmethod
    def encode_definition(cls, value: ControllerObject):
        return encode_id(value.id_chain)

    @classmethod
    def decode_definition(cls, buf, controller, *args, **kwargs):
        id_chain = decode_id(buf)
        return controller.object_at(id_chain)

    def encoded_len(self):
        return self.definition.encoded_len()

    def decode(self, buf):
        return self.definition.decode(buf)

    def encode(self, value):
        return self.definition.encode(value)


class BuiltInObjectTypes:
    # for now, we assume all object types are instantiable. This is not strictly always the case, e.g. system objects
    # that are pre-instantiated may still need to be referred to by type. Will
    # tackle this when needed.

    @classmethod
    def as_id(cls, obj: InstantiableObject):
        return obj.type_id

    @classmethod
    def from_id(cls, type_id) -> InstantiableObject:
        return BuiltInObjectTypes._from_id.get(type_id, None)

    all_types = (CurrentTicks, DynamicContainer, PersistentValue, ValueProfile, LogicActuator, BangBangController,
                 PersistChangeValue, IndirectValue)
    _from_id = dict((x.type_id, x) for x in all_types)


class MixinController(BaseController):

    def __init__(self, connector, objectTypes=BuiltInObjectTypes):
        super().__init__(connector, objectTypes)

    def create_current_ticks(self, container=None, slot=None) -> CurrentTicks:
        return self.create_object(CurrentTicks, None, container, slot)

    def create_dynamic_container(self, container=None, slot=None) -> DynamicContainer:
        return self.create_object(DynamicContainer, None, container, slot)

    def disconnect(self):
        """ forces the underlying connection with the controller to be disconnected. """
        self._connector.disconnect()


class CrossCompileController(MixinController):
    """ additional options only available on the cross-compile """

    def __init__(self, connector):
        super().__init__(connector)


class ArduinoController(MixinController):

    def __init__(self, connector):
        super().__init__(connector)
