# coding: utf-8
import random

__author__ = 'salvia'

import json


class InvalidInstruction(Exception):
    pass


class BadInstructionCall(Exception):
    pass


def str_instruction(self):
    return (
        '<%s instance at %i: opcode=%i, n_arg=%i, mnemonic=%s>' %
        (self.get_name(), id(self), self.opcode, self.n_args, self.mnemonic)
    )


_required_parameters = [
    ('opcode', int),
    ('mnemonic', str),
    ('n_args', int),
    ('arg_types', tuple)
]


def raise_invalid(ins, arg):
    raise InvalidInstruction('Invalid ' + arg + ' for instruction ' + str(ins))


class InstructionMeta(type):
    """
        Instruction metaclass. Defines a str method for instruction classes, and do some creation checks.
    """

    def __str__(self):
        return '<%s at %i: opcode=%i, n_arg=%i, mnemonic=%s, iid=%s>' % (self.__name__, id(self), self.opcode, self.n_args, self.mnemonic, self.iid)

    def __init__(cls, name, bases, dct):
        super(InstructionMeta, cls).__init__(name, bases, dct)
        cls.__str__ = str_instruction
        cls.iid = random.randint(1, 1000000)
        if name != 'Instruction' and name != 'MemberInstruction':
            for par in _required_parameters:
                if dct.get(par[0]) is None or not isinstance(dct.get(par[0]), par[1]):
                    raise_invalid(cls, par[0])
            if len(dct.get('arg_types')) != dct.get('n_args'):
                raise_invalid(cls, 'arg_types')


class Instruction(metaclass=InstructionMeta):
    """
        Base class for all VM instructions. Defines some initilization checks and execution checks.
        It is important to note that Intructions are effectively run upon instantion, i.e. every Instruction instance
        represents some operation that was done inside that. These generally only reside in the commit logs.
    """

    # code of instruction
    opcode = None
    # mnemonic
    mnemonic = None
    # number of arguments
    n_args = None
    # types of the arguments
    arg_types = None

    def __init__(self, *args):
        from .datamodel import Datamodel

        if len(self.arg_types) != self.n_args:
            raise InvalidInstruction('Instruction %s has mismatching .n_args and .arg_types' % (type(self).__name__, ))

        if len(args) != self.n_args:
            raise BadInstructionCall('Wrong number of arguments to ' + str(self))
        for i, arg in enumerate(args):
            if not isinstance(arg, self.arg_types[i]):
                raise BadInstructionCall('Wrong type of arguments to ' + str(self))
        self.args = args
        self.model_args = [arg for arg in args if isinstance(arg, Datamodel)]

    def __call__(self, vm):
        map(lambda model: model._to_user_changing_state(), self.model_args)
        try:
            self.execute(vm, *self.args)
        except Exception as e:
            raise e
        finally:
            map(lambda model: model._to_normal_state(), self.model_args)

    def mnemonize(self):
        return json.dumps(self._mnemonize())

    def _mnemonize(self):
        from dgvm.datamodel import Datamodel, ntuple
        from dgvm.datamodel.meta import DatamodelMeta

        def serialize(a):
            if isinstance(a, DatamodelMeta):
                return ['DatamodelMeta', a.__name__]
            if isinstance(a, Datamodel):
                return [a.__class__.__name__, a.id]
            if isinstance(a, (tuple, ntuple)):
                return list(a)

            return a

        return [self.mnemonic] + [serialize(a) for a in self.args]

    @classmethod
    def load(cls, vm, mnenomic_form):
        parts = json.loads(mnenomic_form)
        return cls._load(vm, parts)

    @classmethod
    def _load(cls, vm, parts):

        cls = vm.instructions['mnemonics'][parts[0]]

        if len(parts) != cls.n_args + 1:
            raise InvalidInstruction('Cannot load mnemonic form: %s' % (parts, ))

        def deserialize(a):
            if isinstance(a, list) and len(a) == 2 and a[0] == 'DatamodelMeta':
                return vm.get_model(a[1])
            if isinstance(a, list) and len(a) == 2 and a[0] in vm.datamodels_idx:
                return vm.get_model(a[0]).get_by_id(vm, a[1])

            return a

        args = parts[1:]
        parsed_args = [deserialize(a) for a in args]

        return cls(*parsed_args)


    @staticmethod
    def execute(cls, vm, *args):

        raise ValueError('Cannot execute base class instruction.')

    @classmethod
    def get_name(cls):
        return cls.__name__


class MemberInstruction(Instruction):

    owner = None
    instances = {}

    def __init__(self, *args):
        super(MemberInstruction, self).__init__(*args)

    def __call__(self, vm):
        list(map(lambda model: model._to_user_changing_state(), self.model_args))
        try:
            self.execute(*self.args)
        except Exception as e:
            raise e
        finally:
            list(map(lambda model: model._to_normal_state(), self.model_args))


    @classmethod
    def get_name(cls):
        return cls.owner.__name__ + '.' + cls.__name__


class MemberInstructionView(object):
    """
        This class is a binding between a datamodel instance and an instruction.
        An instance of MemberInstructionView is returned everytime an user access an member instruction
        in an instance of a Datamodel. (e.g. m = MyDatamodel(); m.my_instruction() )
    """

    def __init__(self, wrapper, instance):
        self.__dict__['wrapper'] = wrapper
        self.__dict__['instance'] = instance

    def __getattr__(self, item):
        return getattr(self.__dict__['wrapper'].i, item)

    def __setattr__(self, key, value):
        return setattr(self.__dict__['wrapper'].i, key, value)

    def __call__(self, *args, **kwargs):
        model_instance = self.__dict__['instance']
        mnemonic_form = self.__dict__['wrapper'].i(model_instance, *args, **kwargs).mnemonize()
        model_instance.vm.execute_from_mnemonic([mnemonic_form])
        return None


class MemberInstructionWrapper(object):
    """
        Wrapper that sits inside a Datamodel when the instruction decorator is used.
    """

    def __init__(self, func, opcode, mnemonic, args):

        # name of the attribute inside the Datamodel
        self.attr_name = ""

        # name of the instruction
        self.name = ""

        # inner isntruction function, defined in the Datamodel. Effectively the decorate function.
        self.func = func

        # instruction opcode
        self.opcode = opcode

        # instruction mnemonic
        self.mnemonic = mnemonic

        # list of argument types received by the instruction
        self.args = args

        # The actual instruction object. inherits from `MemberInstruction` and has a metaclass of `InstructionMeta`
        self.i = None

    def __get__(self, instance, owner):
        """
            If this method is called by an instance of a datamodel, we return an MemberInstructionView, which is a functor
            the user can invoke. This is the use case where we are actually executing an instruction.
            Else, we assume the user is trying to get the instruction itself (something like Datamodel.my_instruction),
            to use for isinstance checks or something. In this case we return the actual instruction object.
        """
        if instance:

            # we only allow the user to execute instructions on live objects, i.e. those that have not been destroyed.
            if instance.is_destroyed():
                from .datamodel.meta import ModelDestroyedError
                raise ModelDestroyedError()
            return MemberInstructionView(self, instance)
        else:
            return self.i

    def __set__(self, instance, value):
        raise ValueError('Cannot set MemberInstruction after its creation')

    def create(self, owner):
        if self.opcode == 101:
            print('================================================>>>> CREATE MOVE 101')
            import traceback
            traceback.print_stack()
        self.i = InstructionMeta(self.func.__name__, (MemberInstruction,), {
            'opcode': self.opcode,
            'mnemonic': self.mnemonic,
            'n_args': len(self.args),
            'arg_types': self.args,
            'owner': owner,
        })
        self.i.execute = staticmethod(self.func)

    def register(self, vm):
        vm.add_instruction(self.i)


class instruction(object):
    """
        Decorator for inline instructions. Returns a MemberInstructionWrapper.
    """

    def __init__(self, opcode, mnemonic, args):
        self.opcode = opcode
        self.mnemonic = mnemonic
        self.args = args

    def __call__(self, func):
        return MemberInstructionWrapper(func, self.opcode, self.mnemonic, self.args)

