# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase
from quodlibet.util.collections import HashedList, DictProxy


class TDictMixin(TestCase):
    uses_mmap = False

    def setUp(self):
        self.fdict = DictProxy()
        self.rdict = {}
        self.fdict["foo"] = self.rdict["foo"] = "bar"

    def test_getsetitem(self):
        self.assertEqual(self.fdict["foo"], "bar")
        self.assertRaises(KeyError, self.fdict.__getitem__, "bar")

    def test_has_key_contains(self):
        assert "foo" in self.fdict
        assert "bar" not in self.fdict
        assert self.fdict.has_key("foo")
        assert not self.fdict.has_key("bar")

    def test_iter(self):
        self.assertEqual(list(iter(self.fdict)), ["foo"])

    def test_clear(self):
        self.fdict.clear()
        self.rdict.clear()
        assert not self.fdict

    def test_keys(self):
        self.assertEqual(list(self.fdict.keys()), list(self.rdict.keys()))

    def test_values(self):
        self.assertEqual(
            list(self.fdict.values()), list(self.rdict.values()))

    def test_items(self):
        self.assertEqual(
            list(self.fdict.items()), list(self.rdict.items()))

    def test_pop(self):
        self.assertEqual(self.fdict.pop("foo"), self.rdict.pop("foo"))
        self.assertRaises(KeyError, self.fdict.pop, "woo")

    def test_pop_bad(self):
        self.assertRaises(TypeError, self.fdict.pop, "foo", 1, 2)

    def test_popitem(self):
        self.assertEqual(self.fdict.popitem(), self.rdict.popitem())
        self.assertRaises(KeyError, self.fdict.popitem)

    def test_update_other(self):
        other = {"a": 1, "b": 2}
        self.fdict.update(other)
        self.rdict.update(other)

    def test_update_other_is_list(self):
        other = [("a", 1), ("b", 2)]
        self.fdict.update(other)
        self.rdict.update(dict(other))

    def test_update_kwargs(self):
        self.fdict.update(a=1, b=2)
        other = {"a": 1, "b": 2}
        self.rdict.update(other)

    def test_setdefault(self):
        self.fdict.setdefault("foo", "baz")
        self.rdict.setdefault("foo", "baz")
        self.fdict.setdefault("bar", "baz")
        self.rdict.setdefault("bar", "baz")

    def test_get(self):
        self.assertEqual(self.rdict.get("a"), self.fdict.get("a"))
        self.assertEqual(
            self.rdict.get("a", "b"), self.fdict.get("a", "b"))
        self.assertEqual(self.rdict.get("foo"), self.fdict.get("foo"))

    def test_repr(self):
        self.assertEqual(repr(self.rdict), repr(self.fdict))

    def test_len(self):
        self.assertEqual(len(self.rdict), len(self.fdict))

    def tearDown(self):
        self.assertEqual(self.fdict, self.rdict)
        self.assertEqual(self.rdict, self.fdict)


class THashedList(TestCase):
    def test_init(self):
        l = HashedList([1, 2, 3])
        assert 1 in l

        l = HashedList()
        assert 1 not in l

    def test_length(self):
        l = HashedList([1, 2, 3, 3])
        self.assertEqual(len(l), 4)

    def test_insert(self):
        l = HashedList([1, 2, 3, 3])
        l.insert(0, 3)
        self.assertEqual(len(l), 5)

    def test_delete(self):
        l = HashedList([2, 2])
        assert 2 in l
        del l[0]
        assert 2 in l
        del l[0]
        assert 2 not in l

    def test_iter(self):
        l = HashedList([1, 2, 3, 3])
        new = list(l)
        self.assertEqual(new, [1, 2, 3, 3])

    def test_del_slice(self):
        l = HashedList([1, 2, 3, 3])
        del l[1:3]
        self.assertEqual(len(l), 2)
        assert 1 in l
        assert 3 in l
        assert 2 not in l

    def test_set_slice(self):
        l = HashedList([1, 2, 3, 3])
        l[:3] = [4]
        assert 4 in l
        assert 3 in l
        assert 2 not in l

    def test_extend(self):
        l = HashedList()
        l.extend([1, 1, 2])
        assert 1 in l
        self.assertEqual(len(l), 3)

    def test_duplicates(self):
        l = HashedList()
        assert not l.has_duplicates()
        l = HashedList(range(10))
        assert not l.has_duplicates()
        l.append(5)
        assert l.has_duplicates()
