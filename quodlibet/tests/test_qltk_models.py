# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from tests import TestCase, add

from quodlibet.qltk.models import ObjectStore, ObjectModelFilter
from quodlibet.qltk.models import ObjectModelSort, ObjectTreeStore


class TObjectStore(TestCase):
    def test_validate(self):
        self.failUnlessRaises(ValueError, ObjectStore, int)
        ObjectStore()
        ObjectStore(object)
        self.failUnlessRaises(ValueError, ObjectStore, object, object)

    def test_column_count(self):
        m = ObjectStore()
        self.failUnlessEqual(m.get_n_columns(), 1)

    def test_empty_append(self):
        m = ObjectStore()
        self.failUnless(m.append())

    def test_append(self):
        m = ObjectStore()
        for i in range(10):
            m.append(row=[i])
        self.failUnlessEqual([r[0] for r in m], range(10))

    def test_append_many(self):
        m = ObjectStore()
        m.append_many(range(10))
        self.failUnlessEqual([r[0] for r in m], range(10))

    def test_iter_append_many(self):
        m = ObjectStore()
        iters = list(m.iter_append_many(range(10)))
        self.failUnlessEqual([r[0] for r in m], range(10))
        values = [m.get_value(i) for i in iters]
        self.failUnlessEqual(values, range(10))

    def test_iter_append_many_iterable_int(self):
        m = ObjectStore()
        for x in m.iter_append_many((i for i in xrange(10))):
            pass
        self.failUnlessEqual([r[0] for r in m], range(10))

    def test_iter_append_many_iterable_object(self):
        objects = [object() for i in xrange(10)]
        m = ObjectStore()
        for x in m.iter_append_many((i for i in objects)):
            pass
        self.failUnlessEqual([r[0] for r in m], objects)

    def test_iter_append_many_empty(self):
        m = ObjectStore()
        for x in m.iter_append_many([]):
            pass

        for x in m.iter_append_many(iter([])):
            pass

    def test_empty_insert(self):
        m = ObjectStore()
        self.failUnless(m.insert(0))

    def test_insert(self):
        m = ObjectStore()
        for i in reversed(range(10)):
            m.insert(0, row=[i])
        self.failUnlessEqual([r[0] for r in m], range(10))

    def test_insert_many(self):
        m = ObjectStore()
        m.append(row=[42])
        m.append(row=[24])
        m.insert_many(1, range(10))
        self.failUnlessEqual([r[0] for r in m], [42] + range(10) + [24])

    def test_insert_many_append(self):
        m = ObjectStore()
        m.insert_many(-1, range(10))
        self.failUnlessEqual([r[0] for r in m], range(10))

        m = ObjectStore()
        m.insert_many(99, range(10))
        self.failUnlessEqual([r[0] for r in m], range(10))

    def test_itervalues(self):
        m = ObjectStore()
        m.insert_many(0, range(10))
        self.failUnlessEqual(range(10), list(m.itervalues()))

    def test_iterrows(self):
        m = ObjectStore()
        m.insert_many(0, range(10))
        for iter_, value in m.iterrows():
            self.failUnlessEqual(m.get_value(iter_), value)

    def test_insert_before(self):
        m = ObjectStore()
        iter_ = m.append(row=[1])
        new_iter = m.insert_before(iter_, [2])
        self.failUnlessEqual(m.get_value(new_iter, 0), 2)
        self.failUnlessEqual([2, 1], list(m.itervalues()))

add(TObjectStore)


class TObjectTreeStore(TestCase):
    def test_validate(self):
        self.failUnlessRaises(ValueError, ObjectTreeStore, int)
        ObjectTreeStore()
        ObjectTreeStore(object)
        self.failUnlessRaises(ValueError, ObjectTreeStore, object, object)

    def test_column_count(self):
        m = ObjectTreeStore()
        self.failUnlessEqual(m.get_n_columns(), 1)

    def test_append_int(self):
        m = ObjectTreeStore()
        m.append(None, row=[1])
        self.failUnlessEqual(list(m.itervalues()), [1])

    def test_append_obj(self):
        m = ObjectTreeStore()
        obj = object()
        m.append(None, row=[obj])
        self.failUnlessEqual(list(m.itervalues()), [obj])

    def test_empty_append(self):
        m = ObjectStore()
        self.failUnless(m.append(None))

add(TObjectTreeStore)


class TObjectModelFilter(TestCase):
    def test_iter_values(self):
        m = ObjectStore()
        f = ObjectModelFilter(child_model=m)
        m.insert_many(0, range(10))
        self.failUnlessEqual(range(10), list(f.itervalues()))

    def test_filter(self):
        m = ObjectStore()
        f = ObjectModelFilter(child_model=m)
        m.insert_many(0, range(10))

        def filter_func(model, iter_, data):
            if model.get_value(iter_) % 2 == 0:
                return True
            return False

        f.set_visible_func(filter_func)
        f.refilter()
        self.failUnlessEqual(range(0, 10, 2), list(f.itervalues()))

add(TObjectModelFilter)


class TObjectModelSort(TestCase):
    def test_iter_values(self):
        m = ObjectStore()
        f = ObjectModelSort(model=m)
        m.insert_many(0, range(10))
        self.failUnlessEqual(range(10), list(f.itervalues()))

    def test_sort(self):
        m = ObjectStore()
        f = ObjectModelSort(model=m)
        m.insert_many(0, range(10))

        def sort_func(model, iter_a, iter_b, data):
            a = model.get_value(iter_a, 0)
            b = model.get_value(iter_b, 0)
            return -cmp(a, b)

        f.set_default_sort_func(sort_func)

        self.failUnlessEqual(sorted(range(10), reverse=True),
                             list(f.itervalues()))

add(TObjectModelSort)
