# coding: utf-8
__author__ = 'salvia'

from .instruction import Instruction, InvalidInstruction


class BeginTransaction(Instruction):
    # BEGINTRANS
    opcode = 1
    mnemonic = 'VM_BEGINTRANS'
    n_args = 0
    arg_types = tuple()

    @classmethod
    def execute(cls, *args):
        pass


class EndTransaction(Instruction):
    # ENDTRANS
    opcode = 2
    mnemonic = 'VM_ENDTRANS'
    n_args = 0
    arg_types = tuple()

    @classmethod
    def execute(cls, *args):
        pass


class InstantiateModel(Instruction):
    # INST model_instance [attributes]
    opcode = 3
    mnemonic = 'INST'
    n_args = 2
    arg_types = (object, dict)

    def __init__(self, *args):
        from dgvm.datamodel.meta import DatamodelMeta
        type(self).arg_types = (DatamodelMeta, dict)
        super(InstantiateModel, self).__init__(*args)

    @classmethod
    def execute(cls, vm, model_instance, attrs):
        pass


class DestroyInstance(Instruction):
    # DESTROY model_instance
    opcode = 4
    mnemonic = 'DESTROY'
    n_args = 2
    arg_types = (object, int)

    def __init__(self, *args):
        from dgvm.datamodel.meta import DatamodelMeta
        type(self).arg_types = (DatamodelMeta, int)
        super(DestroyInstance, self).__init__(*args)

    @classmethod
    def execute(cls, vm, model_class, model_id):

        for name, attr in model_class._vmattrs.items():
            attr._destroy(id=model_id, vm=vm)


#TODO: implement CollapseHeap, an instruction which collapses all treects in the Heap, saving memory and access time,
#TODO: but making commit undo impossible.
