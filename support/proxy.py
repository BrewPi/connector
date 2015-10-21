"""from http://perso.limsi.fr/pointal/python:delegator"""

import inspect
from types import MethodType


class MissingDelegateError(Exception):
    """A delegated method has been called with no delegate object set."""
    pass


def make_delegation_class(model_class, make_subclass=True, deleg_specials=()):
    """Create a new class which methods are simply delegated to an attribute.

    The new class is created as a subclass of the given model_class class
    (unless make_subclass is set to False).
    For each "public" method (ie. those which dont start by an _), or for
    methods listed in deleg_specials, a corresponding method is created in
    the new class, which at runtime will route calls to the delegate object.

    The created class is intended to use as parent class for a class which
    objects need to delegate some services to other objects while providing a
    natural interface as if they provide themselves the service.
    May eventually change delegate objects at runtime.
    """
    servicename = model_class.__name__
    if servicename.endswith('Interface') and servicename != 'Interface':
        servicename = servicename[:-len('Interface')]
    newclassname = servicename + 'Delegation'
    delegateattribute = '_delegate_' + servicename

    # Build new class attributes, __init__,deletage_Xxx method, and a copy
    # of all service methods which must be delegated.
    classdefs = {}
    classdefs['__init__'] = make_init_method(delegateattribute)
    classdefs['delegate_' + servicename] = make_delegate_method(
        delegateattribute, servicename)

    for attname in dir(model_class):
        attval = getattr(model_class, attname)
        if hasattr(attval, '__call__') and \
                (attname in deleg_specials or attname[0] != '_'):
            classdefs[attname] = make_method_wrapper(servicename,
                                                     attval, delegateattribute)

    if make_subclass:
        delegclass = type(newclassname, (model_class,), classdefs)
    else:
        delegclass = type(newclassname, (), classdefs)
    return delegclass


def make_init_method(delegateattribute):
    """Build a new function to use as delegation class __init__() method."""
    # Note: whatever be the delegated service interface class, we dont call its
    # __init__ method, as we are just a wrapper and its the helper class role
    # to correctly initialize things.

    def __init__(self):
        setattr(self, delegateattribute, None)
    return __init__


def make_delegate_method(delegateattribute, servicename):
    """Build a new function to use as delegation classe delegate() method."""

    def delegate_to(self, delegate):
        setattr(self, delegateattribute, delegate)
    delegate_to.__doc__ = "Delegate " + servicename + " to another helper object."
    return delegate_to

srctpl = """\
def {fctname}({args}):
    ""\"{doc}""\"
    # In case delegate class constructor has not been called, use getattr with
    # default to None.
    _delegate_object__ = getattr(self,'{delegattrib}',None)
    if _delegate_object__ is None:
        raise MissingDelegateError("No delegate object for {service} when "
                                   "calling {fctname}")
    return _delegate_object__.{fctname}({params})
"""


def make_method_wrapper(servicename, method, delegateattribute):
    """Build a new function to use as some delegation class method."""
    #FullArgSpec(args, varargs, varkw, defaults, kwonlyargs, kwonlydefaults, annotations)
    fa = inspect.getfullargspec(method)
    methname = method.__name__
    args = []
    params = []

    # Simply copy args names.
    for a in fa.args:
        args.append(a)
        params.append(a)

    # Setup default values for latest named arguments.
    # process by reverse order, with same negative index in both lists.
    if fa.defaults is not None:
        for i in range(-1, -len(fa.defaults) - 1, -1):
            args[i] = args[i] + '=' + repr(fa.defaults[i])

    # Process sequence of variable arguments.
    if fa.varargs:
        args.append("*" + fa.varargs)
        params.append("*" + fa.varargs)

    # Process sequence of named arguments.
    if fa.varkw:
        args.append("**" + fa.varkw)
        params.append("**" + fa.varkw)

    # If missing, make basic documentation.
    doc = inspect.getdoc(method)
    if doc is None:
        doc = "Wrapper for " + servicename + " " + methname + "."

    # Now, create the wrapper method source.
    src = srctpl.format(
        fctname=methname,
        doc=doc,
        service=servicename,
        delegattrib=delegateattribute,
        args=','.join(args),
        params=','.join(params[1:])  # Omit self !
    )

    # print(src)

    #wrappercode = compile(src,"delegator.py","exec")

    methwrapperspace = {}
    exec(src, globals(), methwrapperspace)
    methwrapper = methwrapperspace[methname]

    #methwrapper.__name__ = methname
    #methwrapper.__doc__ = doc
    # methwrapper.__code__ = wrappercode       # We inject our wrapper code.
    #methwrapper.__defaults__ = fa.defaults

    return methwrapper


class Proxy(object):

    def __init__(self, target):
        self._target = target

    def __getattr__(self, aname):
        target = self._target
        f = getattr(target, aname)
        return f if isinstance(f, MethodType) else None
