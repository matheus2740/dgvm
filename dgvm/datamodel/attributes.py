# coding: utf-8
__author__ = 'salvia'

import functools

from .meta import VMAttribute, TypedVMAttribute
from ..utils import to_bytes, to_unicode, iterable


def listof(type):
    return []


class ntuple(object):

    def __init__(self, n, *args):

        if len(args) == 1 and iterable(args[0]):
            args = args[0]
        self.n = n

        self.items = [args[i] if len(args) > i else None for i in range(n)]

    @property
    def x(self):
        try:
            return self[0]
        except KeyError:
            raise AttributeError('x')

    @property
    def y(self):
        try:
            return self[1]
        except KeyError:
            raise AttributeError('y')

    @property
    def z(self):
        try:
            return self[2]
        except KeyError:
            raise AttributeError('z')

    @property
    def u(self):
        try:
            return self[3]
        except KeyError:
            raise AttributeError('u')

    @property
    def v(self):
        try:
            return self[4]
        except KeyError:
            raise AttributeError('v')

    @property
    def w(self):
        try:
            return self[5]
        except KeyError:
            raise AttributeError('w')

    @property
    def t(self):
        try:
            return self[3]
        except KeyError:
            raise AttributeError('t')

    def __getitem__(self, item):

        if isinstance(item, int) and item < self.n:
            return self.items[item]
        else:
            raise KeyError(str(item))

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return self.n

    def __eq__(self, other):
        if iterable(other):
            if len(other) != self.n:
                return False
            for i, item in enumerate(other):
                if item != self[i]:
                    return False
            return True

        return NotImplemented

    def __str__(self):

        return '(' + ', '.join([to_unicode(item) for item in self]) + ')'

    def __repr__(self):
        return str(self)


class Integer(VMAttribute):
    attr_type = int


class String(VMAttribute):
    attr_type = str


class Float(VMAttribute):
    attr_type = float


class Boolean(VMAttribute):
    attr_type = bool


class List(TypedVMAttribute):
    attr_type = staticmethod(listof)


class Pair(TypedVMAttribute):
    attr_type = ntuple
    coerce_function = functools.partial(ntuple, 2)
    coerce_val = True


class Trio(TypedVMAttribute):
    attr_type = ntuple
    coerce_function = functools.partial(ntuple, 3)
    coerce_val = True


class Quartet(TypedVMAttribute):
    attr_type = ntuple
    coerce_function = functools.partial(ntuple, 4)
    coerce_val = True


class Quintet(TypedVMAttribute):
    attr_type = ntuple
    coerce_function = functools.partial(ntuple, 5)
    coerce_val = True


class Sextet(TypedVMAttribute):
    attr_type = ntuple
    coerce_function = functools.partial(ntuple, 6)
    coerce_val = True


class ForeignModel(TypedVMAttribute):

    def _get_wrapped_value(self, instance):
        attr_name = self.attr_name(instance)
        id = instance.vm.heap.get(attr_name)
        return self.subtype.get_by_id(instance.vm, id)
