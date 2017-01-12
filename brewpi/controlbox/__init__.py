"""
Implements a set of proxy objects that attempt to provide an application-level view of the objects in a remote
controller. This API has not been tested extensively, and instead we are moving over to a more lightweight
event API that uses codecs to convert from the on-wire format to an application object.

In other words, this is likely to be in flux.
"""

__author__ = 'mat'
