# Copyright 2013, 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, GObject

from quodlibet.qltk import pygobject_version


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

    if pygobject_version >= (3, 12):
        _value = GObject.Value()
        _value.init(GObject.TYPE_PYOBJECT)

        def _get_marshalable(self, obj, _value=_value):
            if _gets_marshaled_to_pyobject(obj):
                return obj
            _value.set_boxed(obj)
            return _value

        del _value
    else:
        # https://bugzilla.gnome.org/show_bug.cgi?id=703662

        def _get_marshalable(self, obj):
            if _gets_marshaled_to_pyobject(obj):
                return obj
            value = GObject.Value()
            value.init(GObject.TYPE_PYOBJECT)
            value.set_boxed(obj)
            return value


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
        if row:
            value = self._get_marshalable(row[0])
            return self.insert_with_values(parent, 0, [0], [value])
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

    def append(self, row=None):
        if row:
            value = self._get_marshalable(row[0])
            return self.insert_with_valuesv(-1, [0], [value])
        else:
            return super(ObjectStore, self).append(row)

    def insert(self, position, row=None):
        if row:
            value = self._get_marshalable(row[0])
            return self.insert_with_valuesv(position, [0], [value])
        else:
            return super(ObjectStore, self).insert(position)

    def iter_append_many(self, objects):
        """Append a list of python objects, yield iters"""

        insert_with_valuesv = self.insert_with_valuesv
        get_marshalable = self._get_marshalable
        columns = [0]

        try:
            first = next(objects)
        except TypeError:
            try:
                first = objects[0]
            except IndexError:
                return
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
            position = self.get_path(sibling)[0]
            return self.insert_with_valuesv(position, [0], [value])

        return super(ObjectStore, self).insert_before(sibling)

    def insert_after(self, sibling, row=None):
        if row is not None:
            value = self._get_marshalable(row[0])
            position = self.get_path(sibling)[0] + 1
            return self.insert_with_valuesv(position, [0], [value])

        return super(ObjectStore, self).insert_after(sibling)
