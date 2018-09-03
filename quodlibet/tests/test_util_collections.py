# -*- coding: utf-8 -*-
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
        self.failUnlessEqual(self.fdict["foo"], "bar")
        self.failUnlessRaises(KeyError, self.fdict.__getitem__, "bar")

    def test_has_key_contains(self):
        self.failUnless("foo" in self.fdict)
        self.failIf("bar" in self.fdict)
        self.failUnless(self.fdict.has_key("foo"))
        self.failIf(self.fdict.has_key("bar"))

    def test_iter(self):
        self.failUnlessEqual(list(iter(self.fdict)), ["foo"])

    def test_clear(self):
        self.fdict.clear()
        self.rdict.clear()
        self.failIf(self.fdict)

    def test_keys(self):
        self.failUnlessEqual(list(self.fdict.keys()), list(self.rdict.keys()))

    def test_values(self):
        self.failUnlessEqual(
            list(self.fdict.values()), list(self.rdict.values()))

    def test_items(self):
        self.failUnlessEqual(
            list(self.fdict.items()), list(self.rdict.items()))

    def test_pop(self):
        self.failUnlessEqual(self.fdict.pop("foo"), self.rdict.pop("foo"))
        self.failUnlessRaises(KeyError, self.fdict.pop, "woo")

    def test_pop_bad(self):
        self.failUnlessRaises(TypeError, self.fdict.pop, "foo", 1, 2)

    def test_popitem(self):
        self.failUnlessEqual(self.fdict.popitem(), self.rdict.popitem())
        self.failUnlessRaises(KeyError, self.fdict.popitem)

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
        self.failUnlessEqual(self.rdict.get("a"), self.fdict.get("a"))
        self.failUnlessEqual(
            self.rdict.get("a", "b"), self.fdict.get("a", "b"))
        self.failUnlessEqual(self.rdict.get("foo"), self.fdict.get("foo"))

    def test_repr(self):
        self.failUnlessEqual(repr(self.rdict), repr(self.fdict))

    def test_len(self):
        self.failUnlessEqual(len(self.rdict), len(self.fdict))

    def tearDown(self):
        self.failUnlessEqual(self.fdict, self.rdict)
        self.failUnlessEqual(self.rdict, self.fdict)


class THashedList(TestCase):
    def test_init(self):
        l = HashedList([1, 2, 3])
        self.failUnless(1 in l)

        l = HashedList()
        self.failIf(1 in l)

    def test_length(self):
        l = HashedList([1, 2, 3, 3])
        self.failUnlessEqual(len(l), 4)

    def test_insert(self):
        l = HashedList([1, 2, 3, 3])
        l.insert(0, 3)
        self.failUnlessEqual(len(l), 5)

    def test_delete(self):
        l = HashedList([2, 2])
        self.failUnless(2 in l)
        del l[0]
        self.failUnless(2 in l)
        del l[0]
        self.failIf(2 in l)

    def test_iter(self):
        l = HashedList([1, 2, 3, 3])
        new = [a for a in l]
        self.failUnlessEqual(new, [1, 2, 3, 3])

    def test_del_slice(self):
        l = HashedList([1, 2, 3, 3])
        del l[1:3]
        self.failUnlessEqual(len(l), 2)
        self.failUnless(1 in l)
        self.failUnless(3 in l)
        self.failIf(2 in l)

    def test_set_slice(self):
        l = HashedList([1, 2, 3, 3])
        l[:3] = [4]
        self.failUnless(4 in l)
        self.failUnless(3 in l)
        self.failIf(2 in l)

    def test_extend(self):
        l = HashedList()
        l.extend([1, 1, 2])
        self.failUnless(1 in l)
        self.failUnlessEqual(len(l), 3)

    def test_duplicates(self):
        l = HashedList()
        self.failIf(l.has_duplicates())
        l = HashedList(range(10))
        self.failIf(l.has_duplicates())
        l.append(5)
        self.failUnless(l.has_duplicates())
