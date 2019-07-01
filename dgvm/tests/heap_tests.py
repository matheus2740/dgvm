import unittest

from dgvm.data_structures import Heap


class HeapTests(unittest.TestCase):

    def test_history(self):

        t = Heap(128)
        t.checkpoint()
        t[0] = 1

        assert t.get(0) == 1

        t.revert()

        assert t.get(0) is None

        t[0] = 'abcde'

        assert t[0] == 'abcde'

        t.checkpoint()

        t[0] = 'xyz'

        assert t[0] == 'xyz'

        t.revert()

        assert t[0] == 'abcde'


if __name__ == '__main__':
    unittest.main()

















