# coding: utf-8
__author__ = 'salvia'

from dgvm.instruction import MemberInstructionWrapper

from ..constraints import ConstraintCollection
from ..utils import Proxy


class DatamodelStates(object):
    NORMAL = 0
    USER_CHANGING = 1
    ENGINE_CHANGING = 2
    DESTROYED = 3


class DatamodelMeta(type):
    """
        Metaclass for Datamodels. Builds the list of attributes for the model.
    """

    def __init__(cls, name, bases, dct):
        super(DatamodelMeta, cls).__init__(name, bases, dct)
        vmattrs = {}
        member_instructions = []
        dct['_id'] = IDVMAttribute()
        for key, atr in dct.items():
            if key == 'id':
                raise AttributeError('Manual definition of id is not allowed. Model was:' + name)
            if isinstance(atr, VMAttribute):
                atr.set_name(key)
                atr.set_model_name(name)
                vmattrs[key] = atr
            if isinstance(atr, MemberInstructionWrapper):
                atr.create(cls)
                member_instructions.append(atr)
        cls._vmattrs = vmattrs
        cls._member_instructions = member_instructions


class ModelDestroyedError(Exception):
    pass


class VMAttribute(object):

    attr_type = None
    coerce_val = False
    coerce_function = None

    def __init__(self, default=None, null=False, **kwargs):
        self.name = id(self)
        self.model_name = self.__class__.__name__
        self.on_change = ConstraintCollection()
        self.default = default
        self.null = null
        if self.coerce_val and not self.coerce_function:
            self.coerce_function = self.attr_type

    def set_name(self, name):
        self.name = name

    def set_model_name(self, model_name):
        self.model_name = model_name

    def attr_name(self, instance=None, id=None):
        return '%s/O/%i/%s' % (self.model_name, id if id else instance.id, self.name)

    def _get_wrapped_value(self, instance):
        attr_name = self.attr_name(instance)
        return instance.vm.heap.get(attr_name)

    def _set_wrapped_value(self, instance, value):
        from dgvm.datamodel import Datamodel
        attr_name = self.attr_name(instance)
        if isinstance(value, Datamodel):
            value = value.id
        instance.vm.heap.set(attr_name, value)

    def _destroy(self, instance=None, id=None, vm=None):
        attr_name = self.attr_name(instance=instance, id=id)
        if instance:
            vm = instance.vm
        return vm.heap.delete(attr_name)

    def __get__(self, instance, owner):

        if instance._state == DatamodelStates.DESTROYED:
            raise ModelDestroyedError()

        return self._get_wrapped_value(instance)

    def __set__(self, instance, value):

        if self.coerce_val:
            value = self.coerce_function(value)

        def normal():
            raise AttributeError('Cannot set attribute after object creation, build a new object or use Instructions.')

        def user_changing():
            self.on_change.validate(instance, value)
            self._set_wrapped_value(instance, value)

        def engine_changing():
            self._set_wrapped_value(instance, value)

        def destroyed():
            raise ModelDestroyedError()

        actions = {
            DatamodelStates.NORMAL: normal,
            DatamodelStates.USER_CHANGING: user_changing,
            DatamodelStates.ENGINE_CHANGING: engine_changing,
            DatamodelStates.DESTROYED: destroyed
        }

        actions[instance._state]()


class TypedVMAttribute(VMAttribute):

    def __init__(self, subtype, default=None, **kwargs):
        super(TypedVMAttribute, self).__init__(default=default, **kwargs)
        if not subtype:
            raise ValueError('subtype cannot be None')
        if self.coerce_val:
            default = self.coerce_function(default)
        if default and not isinstance(default, self.attr_type):
            raise ValueError('default value must be of type %s, not %s' % (str(self.attr_type), str(type(default))))
        self.subtype = subtype


class IDVMAttribute(VMAttribute):

    def _set_wrapped_value(self, instance, value, id):
        attr_name = self.attr_name(instance, id=id)
        instance.vm.heap.set(attr_name, value)

    def _get_wrapped_value(self, instance, id):
        attr_name = self.attr_name(instance, id=id)
        return instance.vm.heap.get(attr_name)

    def __set__(self, instance, value):
        raise AttributeError('Setting of ID field is not allowed.')


# FIXME:
# TODO: Infantry/OBJ/2/board = <alpha_empire_test.datamodels.board.Board object at 0x10b914f10>


