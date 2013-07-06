# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, GObject

from quodlibet import util


class _ModelMixin(object):

    def get_value(self, iter_, column=0):
        res = super(_ModelMixin, self).get_value(iter_, column)
        # PyGObject 3.4 doesn't unbox in some cases...
        if isinstance(res, GObject.Value):
            res = res.get_boxed()
        return res

    def get_n_columns(self):
        return 1

    def itervalues(self):
        """Yields all values"""

        iter_ = self.get_iter_first()
        getv = self.get_value
        inext = self.iter_next
        while iter_:
            yield getv(iter_)
            iter_ = inext(iter_)


class ObjectModelFilter(_ModelMixin, Gtk.TreeModelFilter):
    pass


class ObjectModelSort(_ModelMixin, Gtk.TreeModelSort):
    pass


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

    def append(self, row=None):
        if row:
            value = GObject.Value()
            value.init(GObject.TYPE_PYOBJECT)
            value.set_boxed(row[0])
            return self.insert_with_valuesv(-1, [0], [value])
        else:
            return super(ObjectStore, self).append(row)

    def insert(self, position, row=None):
        if row:
            value = GObject.Value()
            value.init(GObject.TYPE_PYOBJECT)
            value.set_boxed(row[0])
            return self.insert_with_valuesv(position, [0], [value])
        else:
            return super(ObjectStore, self).insert(position, row)

    def iter_append_many(self, objects):
        """Append a list of python objects, yield iters"""

        insert = self.insert_with_valuesv
        columns = [0]
        type_ = GObject.TYPE_PYOBJECT
        Value = GObject.Value
        for obj in objects:
            value = Value()
            value.init(type_)
            value.set_boxed(obj)
            yield insert(-1, columns, [value])

    def append_many(self, objects):
        """Append a list of python objects"""

        for i in self.iter_append_many(objects):
            pass

    def insert_many(self, position, objects):
        if position == -1 or position > len(self):
            self.append_many(objects)
            return

        insert = self.insert_with_valuesv
        type_ = GObject.TYPE_PYOBJECT
        Value = GObject.Value
        columns = [0]
        for i, obj in enumerate(objects):
            value = Value()
            value.init(type_)
            value.set_boxed(obj)
            insert(position + i, columns, [value])

    def insert_before(self, sibling, row=None):
        treeiter = super(ObjectStore, self).insert_before(sibling)

        if row is not None:
            value = GObject.Value()
            value.init(GObject.TYPE_PYOBJECT)
            value.set_boxed(row[0])
            self.set_value(treeiter, 0, value)

        return treeiter
