# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase

from gi.repository import Gtk

from quodlibet.qltk.models import ObjectStore, ObjectModelFilter
from quodlibet.qltk.models import ObjectModelSort, ObjectTreeStore
from quodlibet.util import cmp


class _TObjectStoreMixin:

    Store = None

    def test_append(self):
        m = self.Store()
        for i in range(10):
            m.append(row=[i])
        self.assertEqual([r[0] for r in m], list(range(10)))

    def test_column_count(self):
        m = self.Store()
        self.assertEqual(m.get_n_columns(), 1)

    def test_insert(self):
        m = self.Store()
        for i in reversed(range(10)):
            m.insert(0, row=[i])
        self.assertEqual([r[0] for r in m], list(range(10)))

    def test_prepend(self):
        m = self.Store()
        for i in reversed(range(10)):
            m.prepend(row=[i])
        self.assertEqual([r[0] for r in m], list(range(10)))

    def test_insert_before(self):
        m = self.Store()
        iter_ = m.append(row=[1])
        new_iter = m.insert_before(iter_, [2])
        self.assertEqual(m.get_value(new_iter, 0), 2)
        self.assertEqual([2, 1], [r[0] for r in m])

    def test_insert_before_noiter(self):
        m = self.Store()
        m.append(row=[1])
        m.insert_before(None, [2])
        self.assertEqual([r[0] for r in m], [1, 2])

    def test_insert_after(self):
        m = self.Store()
        iter_ = m.append(row=[1])
        new_iter = m.insert_after(iter_, [2])
        self.assertEqual(m.get_value(new_iter, 0), 2)
        self.assertEqual([1, 2], [r[0] for r in m])

    def test_insert_after_noiter(self):
        m = self.Store()
        m.append(row=[1])
        m.insert_after(None, [2])
        self.assertEqual([r[0] for r in m], [2, 1])

    def test_allow_nonatomic(self):
        m = self.Store()
        m.ATOMIC = False
        self.assertTrue(m.insert(0))
        self.assertTrue(m.prepend())
        self.assertTrue(m.append())
        self.assertTrue(m.insert_before(None))
        self.assertTrue(m.insert_after(None))


class TOrigObjectStore(TestCase, _TObjectStoreMixin):

    def Store(*x):
        return Gtk.ListStore(object)


class TObjectStore(TestCase, _TObjectStoreMixin):

    Store = ObjectStore

    def test_validate(self):
        self.assertRaises(ValueError, ObjectStore, int)
        ObjectStore()
        ObjectStore(object)
        self.assertRaises(ValueError, ObjectStore, object, object)

    def test_iter_path_changed(self):
        m = ObjectStore()

        def handler(model, path, iter_, result):
            result[0] += 1

        result = [0]
        m.connect("row-changed", handler, result)
        m.append([object()])

        iter_ = m.get_iter_first()
        m.iter_changed(iter_)
        self.assertEqual(result[0], 1)
        m.path_changed(m.get_path(iter_))
        self.assertEqual(result[0], 2)

    def test_append_many(self):
        m = ObjectStore()
        m.append_many(range(10))
        self.assertEqual([r[0] for r in m], list(range(10)))

    def test_append_many_set(self):
        m = ObjectStore()
        m.append_many(set())
        m.append_many(set(range(10)))
        self.assertEqual({r[0] for r in m}, set(range(10)))

    def test_iter_append_many(self):
        m = ObjectStore()
        iters = list(m.iter_append_many(range(10)))
        self.assertEqual([r[0] for r in m], list(range(10)))
        values = [m.get_value(i) for i in iters]
        self.assertEqual(values, list(range(10)))

    def test_iter_append_many_iterable_int(self):
        m = ObjectStore()
        for _x in m.iter_append_many(i for i in range(10)):
            pass
        self.assertEqual([r[0] for r in m], list(range(10)))

    def test_iter_append_many_iterable_object(self):
        objects = [object() for i in range(10)]
        m = ObjectStore()
        for _x in m.iter_append_many(i for i in objects):
            pass
        self.assertEqual([r[0] for r in m], objects)

    def test_iter_append_many_empty(self):
        m = ObjectStore()
        for _x in m.iter_append_many([]):
            pass

        for _x in m.iter_append_many(iter([])):
            pass

    def test_insert_many(self):
        m = ObjectStore()
        m.append(row=[42])
        m.append(row=[24])
        m.insert_many(1, range(10))
        self.assertEqual([r[0] for r in m], [42] + list(range(10)) + [24])

    def test_insert_many_append(self):
        m = ObjectStore()
        m.insert_many(-1, range(10))
        self.assertEqual([r[0] for r in m], list(range(10)))

        m = ObjectStore()
        m.insert_many(99, range(10))
        self.assertEqual([r[0] for r in m], list(range(10)))

    def test_itervalues(self):
        m = ObjectStore()
        m.insert_many(0, range(10))
        self.assertEqual(list(range(10)), list(m.itervalues()))

    def test_itervalues_empty(self):
        m = ObjectStore()
        self.assertEqual(list(m.itervalues()), [])

    def test_iterrows(self):
        m = ObjectStore()
        m.insert_many(0, range(10))
        for iter_, value in m.iterrows():
            self.assertEqual(m.get_value(iter_), value)

    def test_iterrows_empty(self):
        m = ObjectStore()
        self.assertEqual(list(m.iterrows()), [])

    def test_is_empty(self):
        m = ObjectStore()
        self.assertTrue(m.is_empty())
        iter_ = m.append(row=[1])
        self.assertFalse(m.is_empty())
        m.remove(iter_)
        self.assertTrue(m.is_empty())

    def test_nonatomic(self):
        m = ObjectStore()
        self.assertRaises(AssertionError, m.append)
        self.assertRaises(AssertionError, m.insert, 0)
        self.assertRaises(AssertionError, m.prepend)
        self.assertRaises(AssertionError, m.insert_before, None)
        self.assertRaises(AssertionError, m.insert_after, None)

    def test_signal_count(self):
        m = ObjectStore()

        def handler(model, path, iter_, result):
            result[0] += 1

        inserted = [0]
        m.connect("row-inserted", handler, inserted)
        changed = [0]
        m.connect("row-changed", handler, changed)

        m.append([1])
        m.prepend([8])
        m.insert(0, [1])
        m.insert_before(None, [1])
        m.insert_after(None, [1])
        m.insert_many(0, [1, 2, 3])
        m.append_many([1, 2, 3])
        list(m.iter_append_many([1, 2, 3]))
        list(m.iter_append_many(range(3)))

        self.assertEqual(changed[0], 0)
        self.assertEqual(inserted[0], len(m))

    def test__sort_on_value(self):
        m = ObjectStore()
        iter_bob = m.append(row=["bob"])
        iter_alice = m.append(row=["alice"])
        m.append(row=["charlie"])
        result = ObjectStore._sort_on_value(m, iter_alice, iter_bob, None)
        self.assertEqual(result, cmp("alice", "bob"))


class _TObjectTreeStoreMixin:

    Store = None

    def test_column_count(self):
        m = self.Store()
        self.assertEqual(m.get_n_columns(), 1)

    def test_append_int(self):
        m = self.Store()
        m.append(None, row=[1])
        m.append(None, row=[2])
        self.assertEqual([r[0] for r in m], [1, 2])

    def test_append_obj(self):
        m = self.Store()
        obj = object()
        obj2 = object()
        m.append(None, row=[obj])
        m.append(None, row=[obj2])
        self.assertEqual([r[0] for r in m], [obj, obj2])

    def test_insert_after(self):
        m = self.Store()
        iter_ = m.append(None, row=[1])
        new_iter = m.insert_after(None, iter_, [2])
        self.assertEqual(m.get_value(new_iter, 0), 2)
        self.assertEqual([1, 2], [r[0] for r in m])

    def test_insert_after_noroot(self):
        m = self.Store()
        iter_ = m.append(None, row=[1])
        iter2_ = m.append(iter_, row=[2])
        new_iter = m.insert_after(iter_, iter2_, [3])
        self.assertEqual(m.get_value(new_iter, 0), 3)
        self.assertEqual([1], [r[0] for r in m])
        self.assertEqual([2, 3], [r[0] for r in m[0].iterchildren()])

    def test_insert_after_noiter(self):
        m = self.Store()
        m.append(None, row=[1])
        m.insert_after(None, None, [2])
        self.assertEqual([r[0] for r in m], [2, 1])

    def test_insert_before(self):
        m = self.Store()
        iter_ = m.append(None, row=[1])
        new_iter = m.insert_before(None, iter_, [2])
        self.assertEqual(m.get_value(new_iter, 0), 2)
        self.assertEqual([2, 1], [r[0] for r in m])

    def test_insert_before_noroot(self):
        m = self.Store()
        iter_ = m.append(None, row=[1])
        iter2_ = m.append(iter_, row=[2])
        new_iter = m.insert_before(iter_, iter2_, [3])
        self.assertEqual(m.get_value(new_iter, 0), 3)
        self.assertEqual([1], [r[0] for r in m])
        self.assertEqual([3, 2], [r[0] for r in m[0].iterchildren()])

    def test_insert_before_noiter(self):
        m = self.Store()
        m.append(None, row=[1])
        m.insert_before(None, None, [2])
        self.assertEqual([r[0] for r in m], [1, 2])

    def test_allow_nonatomic(self):
        m = self.Store()
        m.ATOMIC = False
        self.assertTrue(m.insert(None, 0))
        self.assertTrue(m.prepend(None))
        self.assertTrue(m.append(None))
        self.assertTrue(m.insert_before(None, None))
        self.assertTrue(m.insert_after(None, None))


class TOrigTreeStore(TestCase, _TObjectTreeStoreMixin):

    def Store(*x):
        return Gtk.TreeStore(object)


class TObjectTreeStore(TestCase, _TObjectTreeStoreMixin):

    Store = ObjectTreeStore

    def test_validate(self):
        self.assertRaises(ValueError, ObjectTreeStore, int)
        ObjectTreeStore()
        ObjectTreeStore(object)
        self.assertRaises(ValueError, ObjectTreeStore, object, object)

    def test_iter_path_changed(self):
        m = ObjectTreeStore()

        def handler(model, path, iter_, result):
            result[0] += 1

        result = [0]
        m.connect("row-changed", handler, result)
        m.append(None, [object()])

        iter_ = m.get_iter_first()
        m.iter_changed(iter_)
        self.assertEqual(result[0], 1)
        m.path_changed(m.get_path(iter_))
        self.assertEqual(result[0], 2)

    def test_itervalues(self):
        m = ObjectTreeStore()
        obj = object()
        obj2 = object()
        it = m.append(None, row=[obj])
        m.append(it, row=[obj2])

        self.assertEqual(list(m.itervalues(None)), [obj])
        self.assertEqual(list(m.itervalues(it)), [obj2])

    def test_iterrows(self):
        m = ObjectTreeStore()
        obj = object()
        obj2 = object()
        it = m.append(None, row=[obj])
        m.append(it, row=[obj2])

        self.assertEqual(list(m.iterrows(None))[0][1], obj)
        self.assertEqual(list(m.iterrows(it))[0][1], obj2)

    def test_nonatomic(self):
        m = ObjectTreeStore()
        self.assertRaises(AssertionError, m.append, None)
        self.assertRaises(AssertionError, m.insert, None, 0)
        self.assertRaises(AssertionError, m.prepend, None)
        self.assertRaises(AssertionError, m.insert_before, None, None)
        self.assertRaises(AssertionError, m.insert_after, None, None)

    def test_signal_count(self):
        m = ObjectTreeStore()

        def handler(model, path, iter_, result):
            result[0] += 1

        inserted = [0]
        m.connect("row-inserted", handler, inserted)
        changed = [0]
        m.connect("row-changed", handler, changed)

        m.append(None, [1])
        m.insert(None, 0, [1])
        m.prepend(None, [1])
        m.insert_before(None, None, [1])
        m.insert_after(None, None, [1])

        self.assertEqual(changed[0], 0)
        self.assertEqual(inserted[0], len(m))

    def test_tree_store_insert_before_none(self):
        store = ObjectTreeStore()
        root = store.append(None, [42])
        sub = store.append(root, [24])

        iter_ = store.insert_before(None, None, [1])
        assert store.get_path(iter_).get_indices() == [1]

        iter_ = store.insert_before(root, None, [1])
        assert store.get_path(iter_).get_indices() == [0, 1]

        iter_ = store.insert_before(sub, None, [1])
        assert store.get_path(iter_).get_indices() == [0, 0, 0]

        iter_ = store.insert_before(None, root, [1])
        assert store.get_path(iter_).get_indices() == [0]

        iter_ = store.insert_before(None, sub, [1])
        assert store.get_path(iter_).get_indices() == [1, 0]

    def test_tree_store_insert_after_none(self):
        store = ObjectTreeStore()
        root = store.append(None, [42])
        sub = store.append(root, [24])

        iter_ = store.insert_after(None, None, [1])
        assert store.get_path(iter_).get_indices() == [0]

        iter_ = store.insert_after(root, None, [1])
        assert store.get_path(iter_).get_indices() == [1, 0]

        iter_ = store.insert_after(sub, None, [1])
        assert store.get_path(iter_).get_indices() == [1, 1, 0]

        iter_ = store.insert_after(None, root, [1])
        assert store.get_path(iter_).get_indices() == [2]

        iter_ = store.insert_after(None, sub, [1])
        assert store.get_path(iter_).get_indices() == [1, 2]


class TObjectModelFilter(TestCase):

    def test_iter_values(self):
        m = ObjectStore()
        f = ObjectModelFilter(child_model=m)
        m.insert_many(0, range(10))
        self.assertEqual(list(range(10)), list(f.itervalues()))

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
        self.assertEqual(list(range(0, 10, 2)), list(f.itervalues()))


class TObjectModelSort(TestCase):

    def test_iter_values(self):
        m = ObjectStore()
        f = ObjectModelSort(model=m)
        m.insert_many(0, range(10))
        self.assertEqual(list(range(10)), list(f.itervalues()))

    def test_sort(self):
        m = ObjectStore()
        f = ObjectModelSort(model=m)
        m.insert_many(0, range(10))

        def sort_func(model, iter_a, iter_b, data):
            a = model.get_value(iter_a, 0)
            b = model.get_value(iter_b, 0)
            return -cmp(a, b)

        f.set_default_sort_func(sort_func)

        self.assertEqual(sorted(range(10), reverse=True),
                             list(f.itervalues()))
