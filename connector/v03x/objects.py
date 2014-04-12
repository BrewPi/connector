from connector.v03x.controller import *
from connector.v03x.time import CurrentTicks, ValueProfile

__author__ = 'mat'


# Now comes the application-specific objects.
# Todo - it would be nice to separate these out, or make it extensible in python
# taken steps in that direction.

class DynamicContainer(EmptyDefinition, UserObject, Container):
    type_id = 4


class PersistentValueBase(BufferDecoder, BufferEncoder):
    def encoded_len(self):
        return 0  # not known


class PersistentValue(NonEmptyBlockDefinition, PersistentValueBase, ReadWriteUserObject):
    type_id = 5


class LogicActuator:
    type_id = 7


class BangBangController:
    type_id = 8


class PersistChangeValue(ReadWriteUserObject, ShortEncoder, ShortDecoder, ReadWriteValue):
    type_id = 9
    shortEnc = ShortEncoder()
    shortDec = ShortDecoder()

    @classmethod
    def encode_definition(cls, arg):
        if arg[1] < 0:
            raise ValueError("threshold < 0")
        return cls.shortEnc.encode(arg[0]) + cls.shortEnc.encode(arg[1])

    @classmethod
    def decode_definition(cls, data_block: bytes):
        return cls.shortDec.decode(data_block[0:2]), cls.shortDec.decode(data_block[2:4])


class BuiltInObjectTypes:
    # for now, we assume all object types are instantiable. This is not strictly always the case, e.g. system objects
    # that are pre-instantiated may still need to be referred to by type. Will tackle this when needed.

    @classmethod
    def as_id(cls, obj: InstantiableObject):
        return obj.type_id

    @classmethod
    def from_id(cls, type_id) -> InstantiableObject:
        return BuiltInObjectTypes._from_id.get(type_id, None)

    all_types = (CurrentTicks, DynamicContainer, PersistentValue, ValueProfile, LogicActuator, BangBangController,
                 PersistChangeValue)
    _from_id = dict((x.type_id, x) for x in all_types)


class MixinController(BaseController):
    def __init__(self, connector):
        super().__init__(connector, BuiltInObjectTypes)

    def create_current_ticks(self, container=None, slot=None) -> CurrentTicks:
        return self.create_object(CurrentTicks, None, container, slot)

    def create_dynamic_container(self, container=None, slot=None) -> DynamicContainer:
        return self.create_object(DynamicContainer, None, container, slot)


class CrossCompileController(MixinController):
    """ additional options only available on the cross-compile """

    def __init__(self, connector):
        super().__init__(connector)


class ArduinoController(MixinController):
    def __init__(self, connector):
        super().__init__(connector)
