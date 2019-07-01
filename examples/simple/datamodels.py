# coding: utf-8
import math

from dgvm.constraints import constraint

__author__ = 'salvia'

from dgvm.datamodel import Datamodel, String, ForeignModel, Integer, Pair
from dgvm.instruction import instruction


class Board(Datamodel):
    width = Integer(default=100)
    height = Integer(default=100)


class Infantry(Datamodel):
    n_units = Integer(null=False)
    attack_dmg = Integer(null=False)
    armor = Integer(null=False)
    health = Integer(null=False)
    action = Integer(null=False)
    tag = String(null=True)
    position = Pair(int, null=False, default=(0, 0))
    board = ForeignModel(Board, null=False)

    @property
    def alive(self):
        return self.health > 0

    def distance_to(self, other):
        dx = (other.position.x - self.position.x) ** 2
        dy = (other.position.y - self.position.y) ** 2
        d = dx + dy
        root = math.sqrt(d)
        return math.ceil(root)

    @instruction(opcode=101, mnemonic='INF.MOVE', args=(Datamodel, int, int))
    def move(self, x, y):
        if not self.alive:
            raise ValueError('Cannot move dead infantry')
        dx = (x - self.position.x) ** 2
        dy = (y - self.position.y) ** 2
        d = dx + dy
        root = math.sqrt(d)
        self.action -= math.ceil(root)
        self.position = (x, y)

    @instruction(opcode=102, mnemonic='INF.ATTK', args=(Datamodel, Datamodel))
    def attack(self, other):

        if self.distance_to(other) > 3:
            raise ValueError('Infantry cannot attack more than 3 units away')

        self.action -= 10
        val = other.health - (self.attack_dmg * self.n_units - other.armor)
        other.health = val


    @constraint.on_change(action)
    def action_limit(cons, old, new, related):
        if new < 0:
            return False
        return True

    @constraint.on_change(position, related=(board,))
    def board_bounds(cons, old, new, related):

        if new.x < 0 or new.y < 0:
            return False

        board = related['board']
        if new.x >= board.width or new.y >= board.height:
            return False

        return True

