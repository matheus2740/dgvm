__author__ = 'Salvia'

import operator


class Proxy(object):
    """
    Original code from: http://code.activestate.com/recipes/496741-object-proxying/
    """
    __slots__ = ["_obj", "__weakref__"]

    def __init__(self, obj):
        self.__dict__["_obj"] = obj

    def reinit(self, obj):
        return type(self)(obj)

    #
    # proxying (special cases)
    #
    def __getattr__(self, name):
        cname = name
        if name.startswith('__'):
            cname = '_' + type(self).__name__ + name
        if cname in self.__dict__:
            return self.__dict__[name]
        return getattr(self.__dict__["_obj"], name)

    def __delattr__(self, name):
        delattr(self.__dict__["_obj"], name)

    def __setattr__(self, name, value):
        setattr(self.__dict__["_obj"], name, value)

    def __nonzero__(self):
        return bool(self.__dict__["_obj"])

    def __str__(self):
        return str(self.__dict__["_obj"])

    def __repr__(self):
        return repr(self.__dict__["_obj"])

    def __eq__(self, other):
        return self.__dict__["_obj"] == other

    #
    # factories
    #
    _special_names = [
        '__abs__', '__add__', '__and__', '__call__', '__cmp__', '__coerce__',
        '__contains__', '__delitem__', '__delslice__', '__div__', '__divmod__',
        '__float__', '__floordiv__', '__ge__', '__getitem__',
        '__getslice__', '__gt__', '__hash__', '__hex__', '__iadd__', '__iand__',
        '__idiv__', '__idivmod__', '__ifloordiv__', '__ilshift__', '__imod__',
        '__imul__', '__int__', '__invert__', '__ior__', '__ipow__', '__irshift__',
        '__isub__', '__iter__', '__itruediv__', '__ixor__', '__le__', '__len__',
        '__long__', '__lshift__', '__lt__', '__mod__', '__mul__', '__ne__',
        '__neg__', '__oct__', '__or__', '__pos__', '__pow__', '__radd__',
        '__rand__', '__rdiv__', '__rdivmod__', '__reduce__', '__reduce_ex__',
        '__repr__', '__reversed__', '__rfloorfiv__', '__rlshift__', '__rmod__',
        '__rmul__', '__ror__', '__rpow__', '__rrshift__', '__rshift__', '__rsub__',
        '__rtruediv__', '__rxor__', '__setitem__', '__setslice__', '__sub__',
        '__truediv__', '__xor__', 'next',
    ]

    _reinit_funcs = {
        '__abs__', '__add__',
        '__contains__', '__delitem__', '__delslice__', '__div__', '__divmod__',
        '__floordiv__',
        '__hex__', '__iadd__', '__iand__',
        '__idiv__', '__idivmod__', '__ifloordiv__', '__ilshift__', '__imod__',
        '__imul__', '__ior__', '__ipow__', '__irshift__',
        '__isub__', '__itruediv__', '__ixor__',
        '__lshift__', '__mod__', '__mul__',
        '__neg__', '__oct__', '__pos__', '__pow__', '__radd__',
        '__rand__', '__rdiv__', '__rdivmod__',
        '__rfloorfiv__', '__rlshift__', '__rmod__',
        '__rmul__', '__ror__', '__rpow__', '__rrshift__', '__rshift__', '__rsub__',
        '__rtruediv__', '__rxor__', '__sub__',
        '__truediv__',
    }

    @classmethod
    def _create_class_proxy(cls, theclass):
        """creates a proxy for the given class"""

        def make_method(name, should_reinit):
            def method(self, *args, **kw):
                if name == '__cmp__':
                    fn = cmp
                else:
                    fn = getattr(operator, name)
                r = fn(self.__dict__["_obj"], *args, **kw)
                if should_reinit:
                    return self.reinit(r)
                else:
                    return r
            return method

        namespace = {}
        for k, v in cls.__dict__.iteritems():
            if not k.startswith('__'):
                namespace[k] = v
        for name in cls._special_names:
            if hasattr(theclass, name) and not hasattr(cls, name):
                namespace[name] = make_method(name, name in cls._reinit_funcs)
        return type("%s(%s)" % (cls.__name__, theclass.__name__), (cls,), namespace)

    def __new__(cls, obj, *args, **kwargs):
        """
        creates an proxy instance referencing `obj`. (obj, *args, **kwargs) are
        passed to this class' __init__, so deriving classes can define an
        __init__ method of their own.
        note: _class_proxy_cache is unique per deriving class (each deriving
        class must hold its own cache)
        """
        try:
            cache = cls.__dict__["_class_proxy_cache"]
        except KeyError:
            cls._class_proxy_cache = cache = {}
        try:
            theclass = cache[obj.__class__]
        except KeyError:
            cache[obj.__class__] = theclass = cls._create_class_proxy(obj.__class__)
        ins = object.__new__(theclass)
        theclass.__init__(ins, obj, *args, **kwargs)
        return ins


def iterable(a):
    try:
        (x for x in a)
        return True
    except TypeError:
        return False


def to_bytes(x):
    if isinstance(x, str):
        return x.encode('utf-8')
    return bytes(x)


def to_unicode(x):
    if isinstance(x, bytes):
        return x.decode('utf-8')
    return str(x)


