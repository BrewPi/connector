from contextlib import closing
import logging
import shelve

__author__ = 'mat'

logger = logging.getLogger(__name__)


def open_shelf():
    return closing(shelve.open("ids"))


def simple_id_service():
    with open_shelf() as shelf:
        new_id = bytes([len(shelf) + 1])       # ensure non-zero
        key = str(new_id)
        shelf[key] = new_id
        return new_id


def return_id(current_id):
    with open_shelf() as shelf:
        key = str(current_id)
        if shelf.get(key):
            del shelf[key]
        else:
            logger.warn("Index %s not found in shelf" % key)
            #raise ValueError("Index %s not found in shelf" % key)
