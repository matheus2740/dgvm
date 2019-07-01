# coding: utf-8
__author__ = 'salvia'

import os
import hashlib
import json
import random
from collections import deque
from functools import partial

from .datamodel.meta import DatamodelMeta
from .data_structures import Heap
from .ipc.client import BaseIPCClient
from .instruction import InvalidInstruction, MemberInstructionWrapper
from .ipc.server import BaseIPCServer
from .builtin_instructions import *
from .datamodel import InvalidModel, Datamodel
from .utils import iterable
import dgvm.datamodel


def file_here(file):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), file)


class Commit(object):

    def __init__(self):
        self.__has_valid_hash = False
        self.__hash = None
        self.__diff = deque()

    def calc_hash(self):
        if not self.__has_valid_hash:
            pre_str = deque()
            for instruction in self.__diff:
                pre_str.append(instruction.mnemonize())

            pre_str = '\n'.join(pre_str)
            pre_str = pre_str.encode('utf-8')
            self.__hash = int(hashlib.sha256(pre_str).hexdigest(), 16)
            self.__has_valid_hash = True
        return self.__hash

    def append(self, item):
        if not isinstance(item, Instruction):
            raise ValueError('Commit item must be of type Instruction, not ' + type(item).__name__)
        self.__has_valid_hash = False
        self.__hash = None
        self.__diff.append(item)

    def extend(self, items):
        if not iterable(items):
            raise ValueError('items must be iterable')

        for item in items:
            self.append(item)

    def dumps(self):
        return json.dumps([i._mnemonize() for i in self.__diff])

    @classmethod
    def loads(cls, vm, dump):
        dat = json.loads(dump)
        c = Commit()
        c.extend([Instruction._load(vm, d) for d in dat])
        return c

    def __len__(self):
        return len(self.__diff)

    def __getitem__(self, item):
        return self.__diff[item]

    def __setitem__(self, key, value):
        raise ValueError('Cannot set a commit item.')

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return self.calc_hash()

    def __str__(self):
        s = []
        for i in range(min(len(self.__diff), 10)):
            s += [str(self.__diff[i])]
        return '<Commit object at %s with instructions: [%s]>' % (id(self), ', '.join(s))

_LIVE_VMS = {}


class LocalVM(object):

    def __init__(self, definitions_package):

        self.instructions_pack = __import__(definitions_package + '.instructions')
        self.datamodels_pack = __import__(definitions_package + '.datamodels')

        self.datamodels = []
        self.datamodels_idx = {}
        self.instructions = {'opcodes': {}, 'mnemonics': {}}

        self.load_instructions()
        self.load_datamodels()

        # initialize heap (16k starting size)
        self.heap = Heap(16384)

        # temporary state of the commit. may be reversed or permanently commited
        self.workspace = None
        # commit history
        self.commits = deque()

        # debugging
        self.verbose = False

    def load_datamodels(self):
        models = deque()
        for k, model in self.datamodels_pack.datamodels.__dict__.items():
            if isinstance(model, DatamodelMeta):
                self.validate_model(model)
                models.append(model)
                for member_instruction in [inst for (name, inst) in model.__dict__.items() if isinstance(inst, MemberInstructionWrapper)]:
                    member_instruction.register(self)

        self.datamodels = list(models)
        self.datamodels_idx = {dm.__name__: dm for dm in models}
        pass

    def validate_model(self, model):
        for m in dgvm.datamodel.model.required_methods:
            if m not in model.__dict__ or model.__dict__[m] is getattr(Datamodel, m):
                raise InvalidModel('%s does not define %s' % (model.__name__, m))

    def load_instructions(self):
        self.instructions = {
            'opcodes': {
                BeginTransaction.opcode: BeginTransaction,
                EndTransaction.opcode: EndTransaction,
                InstantiateModel.opcode: InstantiateModel,
                DestroyInstance.opcode: DestroyInstance
            },
            'mnemonics': {
                BeginTransaction.mnemonic: BeginTransaction,
                EndTransaction.mnemonic: EndTransaction,
                InstantiateModel.mnemonic: InstantiateModel,
                DestroyInstance.mnemonic: DestroyInstance
            }
        }
        for k, v in self.instructions_pack.instructions.__dict__.items():
            if isinstance(v, type) and issubclass(v, Instruction):
                self.add_instruction(v)

    def add_instruction(self, instruction):
        validation = self.validate_instruction(instruction)

        if not validation[0]:
            raise InvalidInstruction(validation[1])

        self.instructions['opcodes'][instruction.opcode] = instruction
        self.instructions['mnemonics'][instruction.mnemonic] = instruction

    def get_instruction(self, mnemonic=None):
        return self.instructions['mnemonics'][mnemonic]

    def get_model(self, name):
        return self.datamodels_idx[name]

    def validate_instruction(self, instruction):

        def fmt(desc):
            return False, '%s: %s' % (desc, str(instruction))

        if instruction.opcode <= 100:
            return fmt('Invalid opcode')
        if not instruction.mnemonic:
            return fmt('Invalid mnemonic')
        if instruction.opcode in self.instructions['opcodes']:
            return fmt('Duplicate opcode')
        if instruction.mnemonic in self.instructions['mnemonics']:
            return fmt('Duplicate mnemonic')

        return True, 'OK'

    # -----

    def begin_transaction(self):
        """
            Start a new commit and adds VM_BEGINTRANS to it (every commit start with an VM_BEGINTRANS instruction)
        """
        if self.workspace:
            raise Exception('Cannot begin transaction with an uncomitted transaction (dirty workspace).')
        self.workspace = Commit()
        self.workspace.append(BeginTransaction())
        self.heap.checkpoint()

    def end_transaction(self):
        """
            Ends the current commit and adds VM_ENDTRANS to it (every commit ends with a VM_ENDTRANS instruction)
        """
        self.workspace.append(EndTransaction())
        self.workspace = None

    def execute(self, instructions):
        if not iterable(instructions):
            raise ValueError('Argument must be a list of instructions, not ' + type(instructions).__name__)
        if not self.workspace:
            self.begin_transaction()

        for instruction in instructions:
            instruction(self)
        self.workspace.extend(instructions)

    def execute_from_mnemonic(self, mnemonic_forms):

        self.execute([Instruction.load(self, mnemonic_form) for mnemonic_form in mnemonic_forms])

    def execute_member_instruction(self, mnemonic, model_instance, args, kwargs):
        i = self.get_instruction(mnemonic=mnemonic)
        m = self.get_model(model_instance[0])
        mi = m.get_by_id(self, model_instance[1])

        self.execute([i(mi, *args, **kwargs)])

    def commit(self):
        if self.workspace:
            self.workspace.calc_hash()
            self.commits.append(self.workspace)
            self.end_transaction()

    def rollback(self):
        if self.workspace:
            self.workspace = self.commits.pop()
        self.heap.revert()

    def get_last_commit(self):
        return self.commits[-1]

    def get_last_commit_dump(self):
        return self.get_last_commit().dumps()

    def get_current_commit(self):
        return self.workspace

    def get_current_commit_dump(self):
        return self.get_current_commit().dumps()

    def heap_size(self):
        return len(self.heap)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class RemoteHeap(object):

    def __init__(self, rvm):

        self.rvm = rvm

    def __getattr__(self, item):
        client_idx = random.randint(0, self.rvm.nclients - 1)
        return partial(self.rvm.clients[client_idx].vm_call_on_heap, self.rvm.definitions_package, item)

    def __len__(self):
        return self.rvm.heap_size()


class RemoteVM(object):

    def __init__(self, definitions_package):

        def make_vm(definitions_package):

            _LIVE_VMS[definitions_package] = LocalVM(definitions_package)

        def vm_call(definitions_package, fn, *args, **kwargs):

            return getattr(_LIVE_VMS[definitions_package], fn)(*args, **kwargs)

        def vm_call_on_heap(definitions_package, fn, *args, **kwargs):

            return getattr(_LIVE_VMS[definitions_package].heap, fn)(*args, **kwargs)

        self.definitions_package = definitions_package
        self.server = BaseIPCServer()
        self.server.register_functor(make_vm, 'make_vm')
        self.server.register_functor(vm_call, 'vm_call')
        self.server.register_functor(vm_call_on_heap, 'vm_call_on_heap')
        self.clients = []
        self.started = False
        self.nclients = 5
        self.heap = RemoteHeap(self)
        self._local_vm = LocalVM(definitions_package)

    def get_last_commit(self):

        dump = self.clients[0].vm_call(self.definitions_package, 'get_last_commit_dump')

        return Commit.loads(self._local_vm, dump)

    def get_current_commit(self):

        dump = self.clients[0].vm_call(self.definitions_package, 'get_current_commit_dump')

        return Commit.loads(self._local_vm, dump)

    def execute(self, instrs):

        self.execute_from_mnemonic([instr.mnemonize() for instr in instrs])

    def startup(self):
        self.server.startup()
        self.clients = [BaseIPCClient() for _ in range(self.nclients)]
        self.clients[0].make_vm(self.definitions_package)
        self.started = False

    def shutdown(self):
        for client in self.clients:
            client.disconnect()
        self.server.shutdown()

    def __enter__(self):
        self.startup()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()

    def __getattr__(self, item):
        client_idx = random.randint(0, self.nclients - 1)
        return partial(self.clients[client_idx].vm_call, self.definitions_package, item)

#TODO: implement commit log/history
#TODO: implement serialization of heap and commit logs
#TODO: implement VM compilation

