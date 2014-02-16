# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, GObject

from quodlibet import util


def _gets_marshaled_to_pyobject(obj,
        _types=(long, float, int, basestring, bool, GObject.Object)):
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

    def get_value(self, iter_, column=0):
        res = super(_ModelMixin, self).get_value(iter_, column)
        # PyGObject 3.4 doesn't unbox in some cases...
        if isinstance(res, GObject.Value):
            res = res.get_boxed()
        return res

    def get_n_columns(self):
        return 1

    def itervalues(self, iter_=None):
        """Yields all values"""

        iter_ = self.iter_children(iter_)
        getv = self.get_value
        inext = self.iter_next
        while iter_:
            yield getv(iter_)
            iter_ = inext(iter_)

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

    def __get_orig_impl(cls, name):
        last = None
        for c in cls.__mro__:
            last = getattr(c, name, last)
        return last

    _orig_append = __get_orig_impl(Gtk.TreeStore, "append")
    _orig_set_value = __get_orig_impl(Gtk.TreeStore, "set_value")

    @util.cached_property
    def _gvalue(self):
        value = GObject.Value()
        value.init(GObject.TYPE_PYOBJECT)
        return value

    def append(self, parent, row=None):
        if row:
            obj = row[0]
            if _gets_marshaled_to_pyobject(obj):
                return self.insert_with_values(parent, 0, [0], row)
            value = self._gvalue
            value.set_boxed(obj)
            iter_ = self._orig_append(parent)
            self._orig_set_value(iter_, 0, value)
            return iter_
        else:
            return super(ObjectTreeStore, self).append(row)


class ObjectStore(_ModelMixin, Gtk.ListStore):
    """Like a ListStore but only supports single column object lists

    Performance related API additions:
     - append_many(), insert_many()
     - itervalues()
    """

    def __init__(self, *args):
        if len(args) > 1:
            raise ValueError
        if args and object not in args and GObject.TYPE_PYOBJECT not in args:
            raise ValueError
        if not args:
            args = [object]
        super(ObjectStore, self).__init__(*args)

    def __get_orig_impl(cls, name):
        last = None
        for c in cls.__mro__:
            last = getattr(c, name, last)
        return last

    _orig_insert = __get_orig_impl(Gtk.ListStore, "insert")
    _orig_append = __get_orig_impl(Gtk.ListStore, "append")
    _orig_set_value = __get_orig_impl(Gtk.ListStore, "set_value")

    @util.cached_property
    def _gvalue(self):
        value = GObject.Value()
        value.init(GObject.TYPE_PYOBJECT)
        return value

    def append(self, row=None):
        if row:
            value = self._gvalue
            value.set_boxed(row[0])
            iter_ = self._orig_append()
            self._orig_set_value(iter_, 0, value)
            return iter_
        else:
            return super(ObjectStore, self).append(row)

    def insert(self, position, row=None):
        if row:
            value = self._gvalue
            value.set_boxed(row[0])
            iter_ = self._orig_insert(position)
            self._orig_set_value(iter_, 0, value)
            return iter_
        else:
            return self._orig_insert(position)

    def iter_append_many(self, objects):
        """Append a list of python objects, yield iters"""

        value = self._gvalue
        append = self._orig_append
        set_value = self._orig_set_value
        set_boxed = value.set_boxed

        try:
            first = next(objects)
        except TypeError:
            try:
                first = objects[0]
            except IndexError:
                return
        else:
            set_boxed(first)
            iter_ = append()
            set_value(iter_, 0, value)
            yield iter_

        # fast path for auto-marshalling
        if _gets_marshaled_to_pyobject(first):
            insert_with_valuesv = self.insert_with_valuesv
            columns = [0]
            for obj in objects:
                yield insert_with_valuesv(-1, columns, [obj])
        else:
            for obj in objects:
                set_boxed(obj)
                iter_ = append()
                set_value(iter_, 0, value)
                yield iter_

    def append_many(self, objects):
        """Append a list of python objects"""

        for i in self.iter_append_many(objects):
            pass

    def insert_many(self, position, objects):
        if position == -1 or position > len(self):
            self.append_many(objects)
            return

        value = self._gvalue
        insert = self._orig_insert
        set_value = self._orig_set_value
        set_boxed = value.set_boxed

        for i, obj in enumerate(objects):
            set_boxed(obj)
            set_value(insert(position + i), 0, value)

    def insert_before(self, sibling, row=None):
        treeiter = super(ObjectStore, self).insert_before(sibling)

        if row is not None:
            value = self._gvalue
            value.set_boxed(row[0])
            self._orig_set_value(treeiter, 0, value)

        return treeiter
