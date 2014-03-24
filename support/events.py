__author__ = 'mat'


class EventHook(object):

    def __init__(self):
        self.__handlers = []

    def __iadd__(self, handler):
        self.__handlers.append(handler)
        return self

    def __isub__(self, handler):
        self.__handlers.remove(handler)
        return self

    def fire(self, *args, **keywargs):
        for handler in self.__handlers:
            handler(*args, **keywargs)

    def clear_object_handlers(self, inObject):
        self.__handlers = [h for h in self.__handlers if h.im_self != inObject]

    def fire_all(self, events):
        for e in events:
            self.fire(e)
