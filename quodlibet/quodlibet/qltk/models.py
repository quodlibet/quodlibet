# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, GObject


class SingleObjectStore(Gtk.ListStore):
    """Like a ListStore but only supports single column object lists"""

    def __init__(self, *args):
        if len(args) > 1:
            raise ValueError
        if args and object not in args and GObject.TYPE_PYOBJECT not in args:
            raise ValueError
        if not args:
            args = [object]
        super(SingleObjectStore, self).__init__(*args)

    def get_n_columns(self):
        return 1

    def append(self, row=None):
        if row:
            value = GObject.Value()
            value.init(GObject.TYPE_PYOBJECT)
            value.set_boxed(row[0])
            return self.insert_with_valuesv(-1, [0], [value])
        else:
            return super(SingleObjectStore, self).append(row)

    def insert(self, position, row=None):
        if row:
            value = GObject.Value()
            value.init(GObject.TYPE_PYOBJECT)
            value.set_boxed(row[0])
            return self.insert_with_valuesv(position, [0], [value])
        else:
            return super(SingleObjectStore, self).insert(position, row)

    def append_many(self, objects):
        """Append a list of python objects"""

        value = GObject.Value()
        value.init(GObject.TYPE_PYOBJECT)
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

        value = GObject.Value()
        value.init(GObject.TYPE_PYOBJECT)
        insert = self.insert_with_valuesv
        vset = value.set_boxed
        columns = [0]
        for i, obj in enumerate(objects):
            vset(obj)
            insert(position + i, columns, [value])
        value.unset()
