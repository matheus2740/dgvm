from dgvm.tests.simple_game_test.datamodels import Infantry, Board, Tank
from dgvm.vm import LocalVM

# Load the definition of the virtual machine.
# The definition is made of models (ORM-like) and instructions (state transition definitions and constraints)
vm = LocalVM('simple')

# create a new board (analogous to a scene/map)
# this could be augmented by a tilemap
board = Board(vm, width=20, height=20)

# create a new infantry squad
squad = Infantry(
    vm,
    n_units=10,
    attack_dmg=3,
    armor=0,
    health=100,
    action=10,
    tag='Hello!',
    board=board,
    position=(1, 1)
)

# another squad
enemy_squad = Infantry(
    vm,
    n_units=6,
    attack_dmg=3,
    armor=0,
    health=60,
    action=10,
    tag='Hello!',
    board=board,
    position=(2, 3)
)

squad.attack(enemy_squad)
pass
