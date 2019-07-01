import os
import unittest
from dgvm.datamodel.meta import ModelDestroyedError
from dgvm.constraints import ConstraintViolation
from dgvm.ipc.client import BaseIPCClient
from dgvm.builtin_instructions import BeginTransaction, EndTransaction, InstantiateModel
from dgvm.ipc.command import IPCServerException
from dgvm.tests.simple_game_test.datamodels.tank import Tank
from dgvm.vm import LocalVM as VM
from dgvm.tests.simple_game_test.datamodels import Infantry, Board
__author__ = 'salvia'


class VMTests(unittest.TestCase):

    def test_commit(self):

        with VM('simple_game_test') as vm:
            i = Infantry(
                vm,
                n_units=1,
                attack_dmg=1,
                armor=0,
                health=1,
                action=10,
                position=(1, 1),
                board=Board(vm, width=20, height=20)
            )

            vm.commit()

            commit = vm.get_last_commit()

            assert hash(commit) is not None
            assert isinstance(commit[0], BeginTransaction)
            assert isinstance(commit[1], InstantiateModel)
            assert isinstance(commit[2], InstantiateModel)
            assert isinstance(commit[3], EndTransaction)
            # TODO: make a full blown check, just like the call below, but for all attributes in the model
            # assert vm.heap[id(i)] == i

    def test_rollback(self):

        with VM('simple_game_test') as vm:
            i = Infantry(
                vm,
                n_units=1,
                attack_dmg=1,
                armor=0,
                health=1,
                action=10,
                position=(1, 1),
                board=Board(vm, width=20, height=20)
            )

            vm.commit()

            commit = vm.get_last_commit()

            assert hash(commit) is not None
            assert isinstance(commit[0], BeginTransaction)
            assert isinstance(commit[1], InstantiateModel)
            assert isinstance(commit[2], InstantiateModel)
            assert isinstance(commit[3], EndTransaction)
            # TODO: make a full blown check, just like the call below, but for all attributes in the model
            # assert vm.heap[id(i)] == i

            i.move(2, 2)

            vm.rollback()

            commit = vm.get_current_commit()

            assert i.position == (1, 1)
            assert hash(commit) is not None
            assert isinstance(commit[0], BeginTransaction)
            assert isinstance(commit[1], InstantiateModel)
            assert isinstance(commit[2], InstantiateModel)
            assert isinstance(commit[3], EndTransaction)
            # TODO: make a full blown check, just like the call below, but for all attributes in the model
            # assert vm.heap['Board/OBJ/1/_id'] == i.id
            pass

    def test_destroy(self):

        with VM('simple_game_test') as vm:
            i = Infantry(
                vm,
                n_units=1,
                attack_dmg=1,
                armor=0,
                health=1,
                action=10,
                position=(1, 1),
                board=Board(vm, width=20, height=20)
            )

            vm.commit()

            commit = vm.get_last_commit()

            assert hash(commit) is not None
            assert isinstance(commit[0], BeginTransaction)
            assert isinstance(commit[1], InstantiateModel)
            assert isinstance(commit[2], InstantiateModel)
            assert isinstance(commit[3], EndTransaction)
            # TODO: make a full blown check, just like the call below, but for all attributes in the model
            # assert vm.heap[id(i)] == i
            try:
                i.destroy()
            except IPCServerException as e:
                print(e.original_tb)
                raise

            vm.commit()

            assert len(vm.heap) == 5  # board object still exists, so actual heap utilized is 5
            assert vm.heap.get('Board/O/1/_id') == 1
            assert vm.heap.get('Board/O/1/height') == 20
            assert vm.heap.get('Board/O/1/width') == 20
            assert vm.heap.get('Infantry/IDCOUNTER') == 1
            assert vm.heap.get('Board/IDCOUNTER') == 1

            try:
                i.move(2, 2)
                assert False
            except ModelDestroyedError:
                pass
            except:
                assert False

    def test_move(self):

        with VM('simple_game_test') as vm:
            i = Infantry(
                vm,
                n_units=1,
                attack_dmg=1,
                armor=0,
                health=1,
                action=10,
                position=(1, 1),
                board=Board(vm, width=20, height=20)
            )

            vm.commit()

            commit = vm.get_last_commit()

            assert hash(commit) is not None
            assert isinstance(commit[0], BeginTransaction)
            assert isinstance(commit[1], InstantiateModel)
            assert isinstance(commit[2], InstantiateModel)
            assert isinstance(commit[3], EndTransaction)
            # TODO: make a full blown check, just like the call below, but for all attributes in the model
            # assert vm.heap[id(i)] == i

            i.move(2, 2)

            vm.commit()

            commit = vm.get_last_commit()

            assert hash(commit) is not None
            assert isinstance(commit[1], Infantry.move)
            assert i.position == (2, 2)
            pass

    def test_constraints(self):

        with VM('simple_game_test') as vm:
            i = Infantry(
                vm,
                n_units=1,
                attack_dmg=1,
                armor=0,
                health=1,
                action=1000,
                position=(1, 1),
                board=Board(vm, width=20, height=20)
            )

            try:
                i.move(21, 21)
                assert False
            except ConstraintViolation as e:
                #assert e.original_message == '<AttributeChangedConstraint: board_bounds on board>'
                pass

            vm.commit()

            commit = vm.get_last_commit()

            assert hash(commit) is not None
            assert isinstance(commit[0], BeginTransaction)
            assert isinstance(commit[1], InstantiateModel)
            assert isinstance(commit[2], InstantiateModel)
            assert isinstance(commit[3], EndTransaction)
            # TODO: make a full blown check, just like the call below, but for all attributes in the model
            # assert vm.heap[id(i)] == i
            assert i.position == (1, 1)
            pass

        with VM('simple_game_test') as vm:
            i = Infantry(
                vm,
                n_units=1,
                attack_dmg=1,
                armor=0,
                health=1,
                action=10,
                position=(1, 1),
                board=Board(vm, width=200, height=200)
            )

            try:
                i.move(100, 100)
                assert False
            except ConstraintViolation as e:
                # assert e.original_message == '<AttributeChangedConstraint: action_limit on action>'
                pass

            vm.commit()

            commit = vm.get_last_commit()

            assert hash(commit) is not None
            assert isinstance(commit[0], BeginTransaction)
            assert isinstance(commit[1], InstantiateModel)
            assert isinstance(commit[2], InstantiateModel)
            assert isinstance(commit[3], EndTransaction)
            # TODO: make a full blown check, just like the call below, but for all attributes in the model
            # assert vm.heap[id(i)] == i
            assert i.position == (1, 1)
            pass

    def test_default_null(self):

        with VM('simple_game_test') as vm:
            i = Infantry(
                vm,
                n_units=1,
                attack_dmg=1,
                armor=0,
                health=1,
                action=10,
                board=Board(vm, width=20, height=20)
            )

            vm.commit()

            commit = vm.get_last_commit()

            assert hash(commit) is not None
            assert isinstance(commit[0], BeginTransaction)
            assert isinstance(commit[1], InstantiateModel)
            assert isinstance(commit[2], InstantiateModel)
            assert isinstance(commit[3], EndTransaction)
            assert i.position == (0, 0)
            assert i.tag == None
            # TODO: make a full blown check, just like the call below, but for all attributes in the model
            # assert vm.heap[id(i)] == i

        with VM('simple_game_test') as vm:
            i = Infantry(
                vm,
                n_units=1,
                attack_dmg=1,
                armor=0,
                health=1,
                action=10,
                tag='Hello!',
                board=Board(vm, width=20, height=20)
            )

            vm.commit()

            commit = vm.get_last_commit()

            assert hash(commit) is not None
            assert isinstance(commit[0], BeginTransaction)
            assert isinstance(commit[1], InstantiateModel)
            assert isinstance(commit[2], InstantiateModel)
            assert isinstance(commit[3], EndTransaction)
            assert i.position == (0, 0)
            assert i.tag == 'Hello!'
            # TODO: make a full blown check, just like the call below, but for all attributes in the model
            # assert vm.heap[id(i)] == i

        with VM('simple_game_test') as vm:
            try:
                i = Infantry(
                    vm,
                    n_units=1,
                    attack_dmg=1,
                    armor=0,
                    action=10,
                    tag='Hello!',
                    board=Board(vm, width=20, height=20)
                )
                assert False
            except ValueError as e:
                assert str(e) == 'Cannot instantiate Infantry: value for health is required.'

    def test_attack(self):

        with VM('simple_game_test') as vm:
            i1 = Infantry(
                vm,
                n_units=1,
                attack_dmg=1,
                armor=0,
                health=1,
                action=10,
                board=Board(vm, width=20, height=20)
            )
            i2 = Infantry(
                vm,
                n_units=1,
                attack_dmg=1,
                armor=0,
                health=10,
                action=10,
                board=Board(vm, width=20, height=20)
            )

            vm.commit()

            try:
                i1.attack(i2)
            except IPCServerException as e:
                print(e.original_tb)
                raise

            vm.commit()

            assert i2.health == 9

            try:
                i1.move(2,2)
                assert False
            except ConstraintViolation as e:
                # assert e.original_message == '<AttributeChangedConstraint: action_limit on action>'
                vm.rollback()

            assert i2.health == 9

    def test_attack_tank(self):

        with VM('simple_game_test') as vm:

            b = Board(vm, width=20, height=20)
            i1 = Infantry(
                vm,
                n_units=1,
                attack_dmg=1,
                armor=0,
                health=10,
                action=10,
                board=b
            )
            try:
                t1 = Tank(
                    vm,
                    attack_dmg=10,
                    armor=0,
                    health=100,
                    action=10,
                    board=b
                )
            except IPCServerException as e:
                print(e.original_tb)
                raise

            vm.commit()

            try:
                t1.attack(i1)
            except IPCServerException as e:
                print(e.original_tb)
                raise

            vm.commit()

            assert i1.health == 0

            try:
                i1.move(2,2)
                assert False
            except ValueError as e:
                # assert e.original_message == 'Cannot move dead infantry'
                vm.rollback()

            assert i1.health == 0


if __name__ == '__main__':
    unittest.main()

