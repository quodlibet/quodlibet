# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from tests import TestCase, add

from quodlibet.qltk.models import SingleObjectStore


class TSingleObjectStore(TestCase):
    def test_validate(self):
        self.failUnlessRaises(ValueError, SingleObjectStore, int)
        SingleObjectStore()
        SingleObjectStore(object)
        self.failUnlessRaises(ValueError, SingleObjectStore, object, object)

    def test_column_count(self):
        m = SingleObjectStore()
        self.failUnlessEqual(m.get_n_columns(), 1)

    def test_empty_append(self):
        m = SingleObjectStore()
        self.failUnless(m.append())

    def test_append(self):
        m = SingleObjectStore()
        for i in range(10):
            m.append(row=[i])
        self.failUnlessEqual([r[0] for r in m], range(10))

    def test_append_many(self):
        m = SingleObjectStore()
        m.append_many(range(10))
        self.failUnlessEqual([r[0] for r in m], range(10))

    def test_empty_insert(self):
        m = SingleObjectStore()
        self.failUnless(m.insert(0))

    def test_insert(self):
        m = SingleObjectStore()
        for i in reversed(range(10)):
            m.insert(0, row=[i])
        self.failUnlessEqual([r[0] for r in m], range(10))

    def test_insert_many(self):
        m = SingleObjectStore()
        m.append(row=[42])
        m.append(row=[24])
        m.insert_many(1, range(10))
        self.failUnlessEqual([r[0] for r in m], [42] + range(10) + [24])

    def test_insert_many_append(self):
        m = SingleObjectStore()
        m.insert_many(-1, range(10))
        self.failUnlessEqual([r[0] for r in m], range(10))

        m = SingleObjectStore()
        m.insert_many(99, range(10))
        self.failUnlessEqual([r[0] for r in m], range(10))

add(TSingleObjectStore)
