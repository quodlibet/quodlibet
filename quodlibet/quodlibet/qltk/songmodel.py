# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk
import gobject

from quodlibet.qltk.playorder import ORDERS


class CustomModel(gtk.GenericTreeModel):
    """Custom TreeModel for a list of python objects

    Instead of a linked list this uses a python list.
    Pros:
        - Fast path/iter access, replacing the whole list is fast.
    Cons:
        - Old iters are never valid after insert/remove/move, except append
        - Slower insert/remove/move/append.

    Integers get used as iters. Since the hash of two can be the same
    while the ID might not, we need a dict to save them:

    print id(1000+1), id(1001), hash(1000+1), hash(1001)

    For fast value access in cellrenderer functions use get_value instead
    of model[iter][0].
    """

    def __init__(self):
        super(CustomModel, self).__init__()
        self.set_property("leak_references", 0)
        self._list = []
        self.__iters = {}
        self.__setdefault = self.__iters.setdefault
        self.invalidate_iters()

    def __len__(self):
        return len(self._list)

    def invalidate_iters(self):
        super(CustomModel, self).invalidate_iters()
        self.__iters.clear()
        self.__iters[len(self) - 1] = None

    def _update_length(self, old):
        del self.__iters[old - 1]
        self.__iters[len(self) - 1] = None

    def on_get_n_columns(self):
        return 1

    def on_get_flags(self):
        return gtk.TREE_MODEL_LIST_ONLY

    def on_get_column_type(self, index):
        if index == 0:
            return gobject.TYPE_PYOBJECT
        return gobject.TYPE_INVALID

    def on_get_iter(self, path):
        path = path[0]
        try:
            self._list[path]
            return self.__setdefault(path - 1, path)
        except IndexError:
            pass

    def on_get_path(self, rowref):
        try:
            self._list[rowref]
            return (rowref,)
        except IndexError:
            pass

    def on_iter_children(self, parent):
        if parent is None and self._list:
            return self.__setdefault(-1, 0)

    def on_iter_has_child(self, rowref):
        return False

    def on_iter_n_children(self, rowref):
        if rowref is None:
            return len(self)
        return 0

    def on_iter_next(self, rowref):
        # this gets called for each row on attach/deattach... has to be fast
        return self.__setdefault(rowref, rowref + 1)

    def on_iter_nth_child(self, parent, n):
        if parent is None:
            return self.__setdefault(n - 1, n)

    def on_iter_parent(self, child):
        return

    def on_get_value(self, rowref, column):
        return self._list[rowref]

    # This shouldn't be needed.., use get_iter
    def create_tree_iter(self, user_data):
        raise NotImplementedError

    # Some fast path overrides
    def get_path(self, iter_):
        return (self.get_user_data(iter_),)

    def get_value(self, iter_, column):
        return self._list[self.get_user_data(iter_)]


class CustomListStore(CustomModel):
    """Provides a gtk.ListStore like API for CustomModel"""

    def set_column_types(self, type_, *args):
        if args or not type_ in (object, gobject.TYPE_PYOBJECT):
            raise ValueError

    def set_value(self, iter_, column, value):
        if column != 0:
            raise ValueError
        index = self.get_user_data(iter_)
        self._list[index] = value
        self.row_changed((index,), iter_)
        return value

    def set(self, iter_, *args):
        if len(args) % 2 != 0:
            raise TypeError
        for i in xrange(0, len(args), 2):
            self.set_value(iter_, args[i], args[i+1])

    def remove(self, iter_):
        path = self.get_path(iter_)
        self._list.pop(path[0])
        self.invalidate_iters()
        self.row_deleted(path)
        return False

    def insert(self, position, row=None):
        value = row and row[0]
        length = len(self)
        if 0 <= position < length:
            self._list.insert(position, value)
            self.invalidate_iters()
        else:
            # appending is the only action that doesn't invalidate iters
            self._list.append(value)
            # None in the iter dict needs to be moved
            self._update_length(length)
            position = length
        iter_ = self.get_iter(position)
        self.row_inserted((position,), iter_)
        return iter_

    def insert_before(self, sibling, row=None):
        if not sibling:
            return self.append(row)
        return self.insert(self.get_user_data(sibling), row)

    def insert_after(self, sibling, row=None):
        if not sibling:
            return self.prepend(row)
        return self.insert(self.get_user_data(sibling) + 1, row)

    def prepend(self, row=None):
        return self.insert(0, row)

    def append(self, row=None):
        return self.insert(len(self), row)

    def clear(self):
        while self._list:
            self._list.pop(0)
            self.invalidate_iters()
            self.row_deleted((0,))

    def reorder(self, new_order):
        # fast but fails for bogus inputs
        self._list = zip(*sorted(zip(new_order, self._list)))[1]
        self.invalidate_iters()
        self.rows_reordered(None, None, new_order)

    def swap(self, a, b):
        ia, ib = self.get_user_data(a), self.get_user_data(b)
        self._list[ia], self._list[ib] = self._list[ib], self._list[ia]
        self.invalidate_iters()
        self.row_deleted((ia,))
        self.row_inserted((ib,), self.get_iter((ia,)))
        self.row_deleted((ib,))
        self.row_inserted((ia,), self.get_iter((ib,)))

    def move_after(self, iter_, position):
        index_src = self.get_user_data(iter_)
        index_dst = position is not None and self.get_user_data(position)
        value = self._list.pop(index_src)
        self.invalidate_iters()
        self.row_deleted((index_src,))
        if position is None:
            self.prepend(row=(value,))
        else:
            if index_dst > index_src:
                index_dst -= 1
            self.insert_after(self.get_iter(index_dst), row=(value,))

    def move_before(self, iter_, position):
        index_src = self.get_user_data(iter_)
        index_dst = position is not None and self.get_user_data(position)
        value = self._list.pop(index_src)
        self.invalidate_iters()
        self.row_deleted((index_src,))
        if position is None:
            self.append(row=(value,))
        else:
            if index_dst > index_src:
                index_dst -= 1
            self.insert_before(self.get_iter(index_dst), row=(value,))


class TrackCurrentModel(CustomListStore):
    """
    Provides methods to set and track an active object in the model
    and to fill/clear without emitting signals.
    (make sure the model isn't attached to a view in those cases)

    Will emit row-changed on target and src if the active object moves/changes.
    """

    __iter = None
    __old_value = None

    def invalidate_iters(self):
        super(TrackCurrentModel, self).invalidate_iters()
        self.__iter = None

    def __contains__(self, song):
        return song in self._list

    def find(self, song):
        try:
            index = self._list.index(song)
        except ValueError:
            return None
        else:
            return self.get_iter(index)

    def find_all(self, songs):
        iters = []
        for i, obj in enumerate(self._list):
            if obj in songs:
                iters.append(self.get_iter(i))
        return iters

    def is_empty(self):
        return not self._list

    @property
    def current(self):
        return self.__iter and self.get_value(self.__iter, 0)

    @property
    def current_path(self):
        return self.__iter and self.get_path(self.__iter)

    def __set_current_iter(self, iter_):
        # emit a row-changed for the previous and the new iter after it is set
        # so that the currentcolumn icon gets updated on song changes
        self.__iter = iter_
        iters = filter(self.iter_is_valid, filter(None, [iter_, self.__iter]))
        for iter_ in iters:
            self.row_changed(self.get_path(iter_), iter_)
        self.__old_value = self.current

    def __get_current_iter(self):
        return self.__iter

    current_iter = property(__get_current_iter, __set_current_iter)

    def remove(self, iter_):
        if not self.current_iter or self.current_iter == iter_:
            super(TrackCurrentModel, self).remove(iter_)
            self.__iter = None
            return False
        current_path = self.current_path[0]
        removed_path = self.get_path(iter_)[0]
        super(TrackCurrentModel, self).remove(iter_)
        if removed_path < current_path:
            new_iter = self.get_iter(current_path - 1)
        else:
            try:
                new_iter = self.get_iter(current_path)
            except ValueError:
                new_iter = None
        self.__iter = new_iter
        return False

    def clear_songs(self):
        """Never call when attached to a view!"""
        self._list = []
        self.invalidate_iters()

    def set_songs(self, songs):
        """Never call when attached to a view!"""
        songs = list(songs)
        print_d("Setting %d songs." % len(songs))
        self._list = songs
        self.invalidate_iters()
        self.__iter = self.__old_value and self.find(self.__old_value)
        print_d("Done filling model.")

    def get_songs(self):
        return list(self._list)

    def clear(self):
        super(TrackCurrentModel, self).clear()

    def set(self, songs):
        self.clear()
        for song in songs:
            self.append(row=(song,))
        self.__iter = self.__old_value and self.find(self.__old_value)

    get = get_songs


class PlaylistModel(TrackCurrentModel):
    order = None
    repeat = False
    sourced = False

    def __init__(self, order=ORDERS[0]):
        super(PlaylistModel, self).__init__()
        self.order = order(self)

        # The playorder plugins use paths atm to remember songs so
        # we need to reset them if the paths change somehow.
        self.__sigs = []
        for sig in ['row-deleted', 'row-inserted', 'rows-reordered']:
            s = self.connect(sig, lambda pl, *x: self.order.reset(pl))
            self.__sigs.append(s)

    def set_songs(self, songs):
        super(PlaylistModel, self).set_songs(songs)
        self.order.reset(self)

    def clear_songs(self):
        super(PlaylistModel, self).clear_songs()
        self.order.reset(self)

    def next(self):
        iter_ = self.current_iter
        self.current_iter = self.order.next_explicit(self, iter_)

    def next_ended(self):
        iter_ = self.current_iter
        self.current_iter = self.order.next_implicit(self, iter_)

    def previous(self):
        iter_ = self.current_iter
        self.current_iter = self.order.previous_explicit(self, iter_)

    def go_to(self, song, explicit=False):
        print_d("Told to go to %r" % getattr(song, "key", song))

        iter_ = None
        if isinstance(song, gtk.TreeIter):
            if not self.iter_is_valid(song):
                print_d("Iter no longer valid for this model!")
            else:
                iter_ = song
        elif song is not None:
            iter_ = self.find(song)

        if iter_:
            self.sourced = True

        if explicit:
            iter_ = self.order.set_explicit(self, iter_)
        else:
            iter_ = self.order.set_implicit(self, iter_)

        self.current_iter = iter_
        return self.current_iter

    def reset(self):
        self.go_to(None)
        self.order.reset(self)
