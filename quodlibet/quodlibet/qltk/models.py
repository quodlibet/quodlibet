# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, GObject


class _ModelMixin(object):

    def get_value(self, iter_, column=0):
        return super(_ModelMixin, self).get_value(iter_, column)

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

        value = GObject.Value()
        value.init(GObject.TYPE_PYOBJECT)
        self.__value = value

    def append(self, row=None):
        if row:
            value = self.__value
            value.set_boxed(row[0])
            return self.insert_with_valuesv(-1, [0], [value])
        else:
            return super(ObjectStore, self).append(row)

    def insert(self, position, row=None):
        if row:
            value = self.__value
            value.set_boxed(row[0])
            return self.insert_with_valuesv(position, [0], [value])
        else:
            return super(ObjectStore, self).insert(position, row)

    def append_many(self, objects):
        """Append a list of python objects"""

        value = self.__value
        insert = self.insert_with_valuesv
        vset = value.set_boxed
        columns = [0]
        for obj in objects:
            vset(obj)
            insert(-1, columns, [value])
        value.unset()

    def insert_many(self, position, objects):
        if position == -1 or position > len(self):
            self.append_many(objects)
            return

        value = self.__value
        insert = self.insert_with_valuesv
        vset = value.set_boxed
        columns = [0]
        for i, obj in enumerate(objects):
            vset(obj)
            insert(position + i, columns, [value])
        value.unset()

    def insert_before(self, sibling, row=None):
        treeiter = super(ObjectStore, self).insert_before(sibling)

        if row is not None:
            value = self.__value
            value.set_boxed(row[0])
            self.set_value(treeiter, 0, value)

        return treeiter
