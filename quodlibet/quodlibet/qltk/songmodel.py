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


class TrackCurrentModel(gtk.ListStore):
    __iter = None
    __old_value = None

    def set(self, songs):
        print_d("Clearing model.")
        self.clear()
        self.__iter = None

        print_d("Setting %d songs." % len(songs))
        insert = self.insert
        oldsong = self.__old_value
        for song in reversed(songs):
            iter_ = insert(0, (song,))
            if song is oldsong:
                self.__iter = iter_
        print_d("Done filling model.")

    def remove(self, iter_):
        if self.__iter and self[iter_].path == self[self.__iter].path:
            self.__iter = None
        super(TrackCurrentModel, self).remove(iter_)

    def get(self):
        return [row[0] for row in self]

    @property
    def current(self):
        return self.__iter and self.get_value(self.__iter, 0)

    @property
    def current_path(self):
        return self.__iter and self.get_path(self.__iter)

    def __set_current_iter(self, iter_):
        # emit a row-changed for the previous and the new iter after it is set
        # so that the currentcolumn icon gets updated on song changes
        for it in filter(None, (self.__iter, iter_)):
            self.row_changed(self.get_path(it), it)
        self.__iter = iter_
        self.__old_value = self.current

    def __get_current_iter(self):
        return self.__iter

    current_iter = property(__get_current_iter, __set_current_iter)

    def find(self, song):
        for row in self:
            if row[0] == song:
                return row.iter
        return None

    def find_all(self, songs):
        return [row.iter for row in self if row[0] in songs]

    def __contains__(self, song):
        return bool(self.find(song))

    def is_empty(self):
        return not len(self)


class PlaylistModel(TrackCurrentModel):
    order = None
    repeat = False
    sourced = False

    def __init__(self):
        super(PlaylistModel, self).__init__(object)
        self.order = ORDERS[0](self)

        # The playorder plugins use paths atm to remember songs so
        # we need to reset them if the paths change somehow.
        self.__sigs = []
        for sig in ['row-deleted', 'row-inserted', 'rows-reordered']:
            s = self.connect(sig, lambda pl, *x: self.order.reset(pl))
            self.__sigs.append(s)

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
            iter_ = song
        elif song is not None:
            iter_ = self.find(song)

        if iter_:
            self.sourced = True

        if explicit:
            self.current_iter = self.order.set_explicit(self, iter_)
        else:
            self.current_iter = self.order.set_implicit(self, iter_)

        return self.current_iter

    def set(self, songs):
        self.order.reset(self)
        map(self.handler_block, self.__sigs)
        super(PlaylistModel, self).set(songs)
        map(self.handler_unblock, self.__sigs)

    def reset(self):
        self.go_to(None)
        self.order.reset(self)
