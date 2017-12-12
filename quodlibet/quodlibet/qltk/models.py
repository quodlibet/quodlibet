# -*- coding: utf-8 -*-
# Copyright 2013, 2014 Christoph Reiter
#           2015, 2017 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk, GObject

from quodlibet.compat import integer_types, string_types, cmp


_auto_types = [float, bool, GObject.Object]
_auto_types.extend(integer_types)
_auto_types.extend(string_types)


def _gets_marshaled_to_pyobject(obj, _types=tuple(_auto_types)):
    """Python objects get automarshalled to GValues which is faster than
    doing it in python but also has its own mapping, because it doesn't
    know the column type of the model.

    This returns if the python objects get marshalled to PYOBJECT
    by the C code.

    The GType logic can be found in 'pyg_type_from_object_strict'
    in PyGObject.
    """

    if obj is None:
        return False

    return not isinstance(obj, _types)


class _ModelMixin(object):

    ATOMIC = True
    """Guard against unintentional non-atomic row inserts.

    Set to False if you know what you're doing.
    """

    def get_value(self, iter_, column=0, _base=Gtk.TreeModel.get_value):
        return _base(self, iter_, column)

    def get_n_columns(self):
        return 1

    def iter_changed(self, iter_):
        """Like row_changed(), but only needs a Gtk.TreeIter"""

        self.row_changed(self.get_path(iter_), iter_)

    def path_changed(self, path):
        """Like row_changed(), but only needs a Gtk.TreePath"""

        self.row_changed(path, self.get_iter(path))

    def itervalues(self, iter_=None):
        """Yields all values"""

        iter_ = self.iter_children(iter_)
        getv = self.get_value
        inext = self.iter_next
        while iter_:
            yield getv(iter_)
            iter_ = inext(iter_)

    def values(self):
        """Largely for PY2 -> PY3 compatibility"""
        return list(self.itervalues())

    def iterrows(self, iter_=None):
        """Yields (iter, value) tuples"""

        iter_ = self.iter_children(iter_)
        getv = self.get_value
        inext = self.iter_next
        while iter_:
            yield iter_, getv(iter_)
            iter_ = inext(iter_)

    def is_empty(self):
        return not self.get_iter_first()

    _value = GObject.Value()
    _value.init(GObject.TYPE_PYOBJECT)

    def _get_marshalable(self, obj, _value=_value):
        if _gets_marshaled_to_pyobject(obj):
            return obj
        _value.set_boxed(obj)
        return _value

    del _value


class ObjectModelFilter(_ModelMixin, Gtk.TreeModelFilter):
    pass


class ObjectModelSort(_ModelMixin, Gtk.TreeModelSort):
    pass


class ObjectTreeStore(_ModelMixin, Gtk.TreeStore):
    def __init__(self, *args):
        if len(args) > 1:
            raise ValueError
        if args and object not in args and GObject.TYPE_PYOBJECT not in args:
            raise ValueError
        if not args:
            args = [object]
        super(ObjectTreeStore, self).__init__(*args)

    def append(self, parent, row=None):
        if row is not None:
            value = self._get_marshalable(row[0])
            return self.insert_with_values(parent, -1, [0], [value])
        else:
            assert not self.ATOMIC
            return super(ObjectTreeStore, self).append(parent)

    def insert(self, parent, position, row=None):
        if row is not None:
            value = self._get_marshalable(row[0])
            return self.insert_with_values(parent, position, [0], [value])
        else:
            assert not self.ATOMIC
            return super(ObjectTreeStore, self).insert(parent, position)

    def prepend(self, parent, row=None):
        return self.insert(parent, 0, row)

    def insert_before(self, parent, sibling, row=None):
        if row is not None:
            value = self._get_marshalable(row[0])
            if sibling is None:
                position = -1
            else:
                position = self.get_path(sibling)[-1]
            return self.insert_with_values(parent, position, [0], [value])

        assert not self.ATOMIC
        return super(ObjectTreeStore, self).insert_before(parent, sibling)

    def insert_after(self, parent, sibling, row=None):
        if row is not None:
            value = self._get_marshalable(row[0])
            if sibling is None:
                position = 0
            else:
                position = self.get_path(sibling)[-1] + 1
            return self.insert_with_values(parent, position, [0], [value])

        assert not self.ATOMIC
        return super(ObjectTreeStore, self).insert_after(parent, sibling)


class ObjectStore(_ModelMixin, Gtk.ListStore):
    """Like a ListStore but only supports single column object lists

    Performance related API additions:
     - append_many(), insert_many()
     - itervalues()
    """

    @staticmethod
    def _sort_on_value(m, a, b, data):
        """Sorts two items in an ObjectStore,
        suitable for passing to `set_default_sort_func`"""
        return cmp(m[a][0], m[b][0])

    def __init__(self, *args):
        if len(args) > 1:
            raise ValueError
        if args and object not in args and GObject.TYPE_PYOBJECT not in args:
            raise ValueError
        if not args:
            args = [object]
        super(ObjectStore, self).__init__(*args)

    def append(self, row=None):
        if row:
            value = self._get_marshalable(row[0])
            return self.insert_with_valuesv(-1, [0], [value])
        else:
            assert not self.ATOMIC
            return super(ObjectStore, self).append(row)

    def insert(self, position, row=None):
        if row:
            value = self._get_marshalable(row[0])
            return self.insert_with_valuesv(position, [0], [value])
        else:
            assert not self.ATOMIC
            return super(ObjectStore, self).insert(position)

    def iter_append_many(self, objects):
        """Append a list of python objects, yield iters"""

        insert_with_valuesv = self.insert_with_valuesv
        get_marshalable = self._get_marshalable
        columns = [0]

        try:
            first = next(objects)
        except TypeError:
            first = next(iter(objects))
        else:
            value = get_marshalable(first)
            yield insert_with_valuesv(-1, columns, [value])

        # fast path for auto-marshalling
        if _gets_marshaled_to_pyobject(first):
            for obj in objects:
                yield insert_with_valuesv(-1, columns, [obj])
        else:
            for obj in objects:
                value = get_marshalable(obj)
                yield insert_with_valuesv(-1, columns, [value])

    def append_many(self, objects):
        """Append a list of python objects"""

        for i in self.iter_append_many(objects):
            pass

    def insert_many(self, position, objects):
        if position == -1 or position > len(self):
            self.append_many(objects)
            return

        insert_with_valuesv = self.insert_with_valuesv
        get_marshalable = self._get_marshalable
        columns = [0]

        for i, obj in enumerate(objects):
            value = get_marshalable(obj)
            insert_with_valuesv(position + i, columns, [value])

    def insert_before(self, sibling, row=None):
        if row is not None:
            value = self._get_marshalable(row[0])
            if sibling is None:
                position = -1
            else:
                position = self.get_path(sibling)[0]
            return self.insert_with_valuesv(position, [0], [value])

        assert not self.ATOMIC
        return super(ObjectStore, self).insert_before(sibling)

    def insert_after(self, sibling, row=None):
        if row is not None:
            value = self._get_marshalable(row[0])
            if sibling is None:
                position = 0
            else:
                position = self.get_path(sibling)[0] + 1
            return self.insert_with_valuesv(position, [0], [value])

        assert not self.ATOMIC
        return super(ObjectStore, self).insert_after(sibling, row)

    def prepend(self, row=None):
        return self.insert(0, row)
