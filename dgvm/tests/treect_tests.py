import unittest

from dgvm.data_structures import Treect


class TreectTests(unittest.TestCase):

    def test_base_keys(self):

        t = Treect()
        t['a'] = 1
        t[2] = 22

        assert t['a'] == 1
        assert t[2] == 22
        assert 1 == t.get('a')
        assert 22 == t.get(2)
        assert t.get('non-existent-key') is None

    def test_first_level(self):

        t = Treect()
        t['a/b'] = 1
        t['a/2'] = 22

        assert t['a/b'] == 1
        assert t['a/2'] == 22
        assert 1 == t.get('a/b')
        assert 22 == t.get('a/2')
        assert isinstance(t.get('a'), Treect)
        assert isinstance(t['a'], Treect)
        assert t.get('a')['b'] == 1
        assert t.get('a')['2'] == 22

        try:
            ne = t['non-existent-bucket']
            assert False
        except KeyError:
            pass

    def test_many_levels(self):

        t = Treect()
        t['a/b/c/d/e'] = 1

        assert t['a/b/c/d/e'] == 1
        assert 1 == t.get('a/b/c/d/e')
        assert isinstance(t.get('a'), Treect)
        assert isinstance(t['a'], Treect)
        assert isinstance(t['a'].get('b'), Treect)
        assert isinstance(t['a']['b']['c'], Treect)
        assert isinstance(t.get('a').get('b').get('c').get('d'), Treect)
        assert t.get('a')['b/c/d/e'] == 1
        assert t.get('a')['b/c']['d/e'] == 1
        assert t.get('a').get('b')['c/d/e'] == 1
        assert t.get('a').get('b').get('c')['d/e'] == 1
        assert t.get('a').get('b').get('c').get('d')['e'] == 1

    def test_iteration(self):

        t = Treect()

        t['a'] = 1
        t['b'] = 2
        t['c'] = 3
        t['d'] = 4
        t['e'] = 5
        t['2/a'] = 1
        t['2/b'] = 2
        t['2/c'] = 3
        t['2/d'] = 4
        t['2/e'] = 5
        t['3/2/a'] = 1
        t['3/2/b'] = 2
        t['3/2/c'] = 3
        t['3/2/d'] = 4
        t['3/2/e'] = 5

        for k, v in t.items():
            if k in 'abcde':
                assert ord(k) == 97 + v - 1
            if k == '2':
                assert isinstance(v, Treect)
                for k2, v2 in v.items():
                    assert ord(k2) == 97 + v2 - 1
            if k == '3':
                assert isinstance(v, Treect)
                for k2, v2 in v['2'].items():
                    assert ord(k2) == 97 + v2 - 1

    def test_iteration_all(self):

        t = Treect()

        t['a'] = 1
        t['b'] = 2
        t['c'] = 3
        t['d'] = 4
        t['e'] = 5
        t['2/f'] = 6
        t['2/g'] = 7
        t['2/h'] = 8
        t['2/i'] = 9
        t['2/j'] = 10
        t['3/2/k'] = 11
        t['3/2/l'] = 12
        t['3/2/m'] = 13
        t['3/2/n'] = 14
        t['3/2/o'] = 15

        for k, v in t.all_items():
            assert ord(k[-1]) == 97 + v - 1

    def test_len(self):

        t = Treect()

        t['a'] = 1
        t['b'] = 2
        t['c'] = 3
        t['d'] = 4
        t['e'] = 5
        t['2/a'] = 1
        t['2/b'] = 2
        t['2/c'] = 3
        t['2/d'] = 4
        t['2/e'] = 5
        t['3/2/a'] = 1
        t['3/2/b'] = 2
        t['3/2/c'] = 3
        t['3/2/d'] = 4
        t['3/2/e'] = 5

        assert len(t) == 7
        assert len(t['2']) == 5
        assert len(t['3']) == 1
        assert len(t['3']['2']) == 5
        assert len(t['3/2']) == 5
        assert len(list(t.all_items())) == 15

    def test_compare(self):

        t = Treect()
        t['a/b/c/d/e'] = 1
        t['b'] = 2
        t['c'] = 3
        t['d'] = 4
        t['e'] = 5
        t['2/b'] = 2
        t['2/c'] = 3
        t['2/d'] = 4
        t['2/e'] = 5

        t2 = Treect()
        t2['b'] = 2
        t2['c'] = 3
        t2['d'] = 4
        t2['e'] = 5

        t3 = Treect()
        t3['a/b/c/d/e'] = 1
        t3['b'] = 2
        t3['c'] = 3
        t3['d'] = 4
        t3['e'] = 5
        t3['2/b'] = 2
        t3['2/c'] = 3
        t3['2/d'] = 4
        t3['2/e'] = 5

        assert t == t
        assert t == t3
        assert t != t2
        assert t2 != t3
        assert t['2'] == t2
        assert t['a/b'] == t.get('a')['b']

    def test_constructor(self):

        t = Treect(a__b=1, a__2=22, c=3)

        assert t['a/b'] == 1
        assert t['a/2'] == 22
        assert t['c'] == 3
        assert 1 == t.get('a/b')
        assert 22 == t.get('a/2')
        assert 3 == t.get('c')
        assert isinstance(t.get('a'), Treect)
        assert isinstance(t['a'], Treect)
        assert t.get('a')['b'] == 1
        assert t.get('a')['2'] == 22
        assert t.get('c') == 3

        try:
            ne = t['non-existent-bucket']
            assert False
        except KeyError:
            pass

    def test_to_dict(self):

        t = Treect()

        t['a'] = 1
        t['b'] = 2
        t['c'] = 3
        t['d'] = 4
        t['e'] = 5
        t['2/a'] = 1
        t['2/b'] = 2
        t['2/c'] = 3
        t['2/d'] = 4
        t['2/e'] = 5
        t['3/2/a'] = 1
        t['3/2/b'] = 2
        t['3/2/c'] = 3
        t['3/2/d'] = 4
        t['3/2/e'] = 5

        assert t.to_dict() == {
            'a': 1,
            'b': 2,
            'c': 3,
            'd': 4,
            'e': 5,
            '2': {
                'a': 1,
                'b': 2,
                'c': 3,
                'd': 4,
                'e': 5,
            },
            '3': {
                '2': {
                    'a': 1,
                    'b': 2,
                    'c': 3,
                    'd': 4,
                    'e': 5,
                },
            }
        }

    def test_from_dict(self):

        t = Treect()

        t['a'] = 1
        t['b'] = 2
        t['c'] = 3
        t['d'] = 4
        t['e'] = 5
        t['2/a'] = 1
        t['2/b'] = 2
        t['2/c'] = 3
        t['2/d'] = 4
        t['2/e'] = 5
        t['3/2/a'] = 1
        t['3/2/b'] = 2
        t['3/2/c'] = 3
        t['3/2/d'] = 4
        t['3/2/e'] = 5

        d = {
            'a': 1,
            'b': 2,
            'c': 3,
            'd': 4,
            'e': 5,
            '2': {
                'a': 1,
                'b': 2,
                'c': 3,
                'd': 4,
                'e': 5,
            },
            '3': {
                '2': {
                    'a': 1,
                    'b': 2,
                    'c': 3,
                    'd': 4,
                    'e': 5,
                },
            }
        }
        t2 = Treect.from_dict(d)

        t3 = Treect(d)

        assert t == t2 == t3

if __name__ == '__main__':
    unittest.main()

















