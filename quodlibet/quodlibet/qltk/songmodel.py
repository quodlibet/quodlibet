# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk
import gobject

from quodlibet.qltk.playorder import ORDERS


class PlaylistMux(object):

    def __init__(self, player, q, pl):
        self.q = q
        self.pl = pl
        player.connect('song-started', self.__check_q)

    def __check_q(self, player, song):
        if song is not None:
            iter = self.q.find(song)
            if iter: self.q.remove(iter)
            self.q.reset()

    def get_current(self):
        if self.q.current is not None: return self.q.current
        else: return self.pl.current

    current = property(get_current)

    def next(self):
        if self.q.is_empty():
            self.pl.next()
            self.q.sourced = False
            self.pl.sourced = True
        elif self.q.current is None:
            self.q.next()
            self.q.sourced = True
            self.pl.sourced = False

    def next_ended(self):
        if self.q.is_empty():
            self.pl.next_ended()
            self.q.sourced = False
            self.pl.sourced = True
        elif self.q.current is None:
            self.q.next()
            self.q.sourced = True
            self.pl.sourced = False

    def previous(self):
        self.pl.previous()

    def go_to(self, song, explicit=False):
        print_d("Told to go to %r" % getattr(song, "key", song))
        self.q.go_to(None)
        return self.pl.go_to(song, explicit)

    def reset(self):
        self.pl.reset()
        self.q.go_to(None)
        if not self.pl.is_empty():
            self.next()

    def enqueue(self, songs):
        for song in songs:
            self.q.append(row=[song])

    def unqueue(self, songs):
        map(self.q.remove, filter(None, map(self.q.find, songs)))


class PlaylistModel(gtk.ListStore):
    order = None
    repeat = False
    sourced = False
    __iter = None
    __old_value = None

    __gsignals__ = {
        'songs-set': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ())
        }

    def __init__(self):
        super(PlaylistModel, self).__init__(object)
        self.order = ORDERS[0](self)

        # The playorder plugins use paths atm to remember songs so
        # we need to reset them if the paths change somehow.
        self.__sigs = []
        for sig in ['row-deleted', 'row-inserted', 'rows-reordered']:
            s = self.connect(sig, lambda pl, *x: self.order.reset(pl))
            self.__sigs.append(s)

    def set(self, songs):
        oldsong = self.current
        if oldsong is None: oldsong = self.__old_value
        else: self.__old_value = oldsong
        self.order.reset(self)
        self.current_iter = None

        # We just reset the order manually so block the signals
        map(self.handler_block, self.__sigs)
        print_d("Clearing model.", context=self)
        self.clear()
        print_d("Setting %d songs." % len(songs), context=self)
        insert = self.insert
        for song in reversed(songs):
            iter = insert(0, (song,))
            if song is oldsong:
                self.current_iter = iter
        if self.__iter is not None:
            self.__old_value = None
        print_d("Done filling model.", context=self)
        map(self.handler_unblock, self.__sigs)
        self.emit('songs-set')

    def reverse(self):
        if not len(self): return
        self.order.reset(self)
        map(self.handler_block, self.__sigs)
        self.reorder(range(len(self)-1, -1, -1))
        map(self.handler_unblock, self.__sigs)

    def remove(self, iter):
        if self.__iter and self[iter].path == self[self.__iter].path:
            self.current_iter = None
        super(PlaylistModel, self).remove(iter)

    def get(self):
        return [row[0] for row in self]

    def get_current(self):
        if self.__iter is None: return None
        elif self.is_empty(): return None
        else: return self[self.__iter][0]

    current = property(get_current)

    def get_current_path(self):
        if self.__iter is None: return None
        elif self.is_empty(): return None
        else: return self[self.__iter].path
    current_path = property(get_current_path)

    def __set_current_iter(self, iter_):
        # emit a row-changed for the previous and the new iter after it is set
        # so that the currentcolumn icon gets updated on song changes
        old_iter = self.current_iter
        self.__iter = iter_
        for iter_ in filter(None, (self.__iter, old_iter)):
            self.row_changed(self.get_path(iter_), iter_)

    def get_current_iter(self):
        if self.__iter is None: return None
        elif self.is_empty(): return None
        else: return self.__iter
    current_iter = property(get_current_iter, __set_current_iter)

    def next(self):
        self.current_iter = self.order.next_explicit(self, self.__iter)

    def next_ended(self):
        self.current_iter = self.order.next_implicit(self, self.__iter)

    def previous(self):
        self.current_iter = self.order.previous_explicit(self, self.__iter)

    def go_to(self, song, explicit=False):
        print_d("Told to go to %r" % getattr(song, "key", song))
        self.current_iter = None
        if isinstance(song, gtk.TreeIter):
            self.current_iter = song
            self.sourced = True
        elif song is not None:
            for row in self:
                if row[0] == song:
                    self.current_iter = row.iter
                    print_d("Found song at %r" % row, context=self)
                    self.sourced = True
                    break
            else:
                print_d("Failed to find song", context=self)
        if explicit:
            self.current_iter = self.order.set_explicit(self, self.__iter)
        else:
            self.current_iter = self.order.set_implicit(self, self.__iter)
        return self.__iter

    def find(self, song):
        for row in self:
            if row[0] == song: return row.iter
        return None

    def find_all(self, songs):
        return [row.iter for row in self if row[0] in songs]

    def __contains__(self, song):
        return bool(self.find(song))

    def is_empty(self):
        return not len(self)

    def reset(self):
        self.go_to(None)
        self.order.reset(self)
