__author__ = 'salvia'

from dgvm.datamodel import Datamodel
from dgvm.datamodel import Integer, Pair


class Board(Datamodel):
    """
    Preliminary board datamodel,
    used to test DGVM
    """
    width = Integer()
    height = Integer()

