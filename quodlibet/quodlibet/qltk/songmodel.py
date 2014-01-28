# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import itertools

from gi.repository import Gtk

from quodlibet.qltk.playorder import ORDERS
from quodlibet.qltk.models import ObjectStore


def check_sourced(func):
    # Validate sourced flags after each action that could lead to a changed
    # iter (only ones triggerd by the order, no iter removal!)
    def wrap(self, *args, **kwargs):
        res = func(self, *args, **kwargs)
        if self.q.current is not None:
            self.q.sourced = True
            self.pl.sourced = False
        else:
            self.q.sourced = False
            self.pl.sourced = True
        return res
    return wrap


class PlaylistMux(object):

    def __init__(self, player, q, pl):
        self.q = q
        self.pl = pl
        player.connect('song-started', self.__check_q)

    def __check_q(self, player, song):
        if song is not None:
            iter = self.q.find(song)
            if iter:
                self.q.remove(iter)
            self.q.reset()

    def get_current(self):
        if self.q.current is not None:
            return self.q.current
        else:
            return self.pl.current

    current = property(get_current)

    @check_sourced
    def next(self):
        if self.q.is_empty():
            self.pl.next()
        elif self.q.current is None:
            self.q.next()

    @check_sourced
    def next_ended(self):
        if self.q.is_empty():
            self.pl.next_ended()
        elif self.q.current is None:
            self.q.next()

    @check_sourced
    def previous(self):
        self.pl.previous()

    @check_sourced
    def go_to(self, song, explicit=False):
        print_d("Told to go to %r" % getattr(song, "key", song))
        self.q.go_to(None)
        return self.pl.go_to(song, explicit)

    @check_sourced
    def reset(self):
        self.q.go_to(None)
        self.pl.reset()

    def enqueue(self, songs):
        self.q.append_many(songs)

    def unqueue(self, songs):
        q = self.q
        for iter_ in q.find_all(songs):
            q.remove(iter_)


class TrackCurrentModel(ObjectStore):
    __iter = None
    __old_value = None

    def set(self, songs):
        print_d("Clearing model.")
        self.clear()
        self.__iter = None

        print_d("Setting %d songs." % len(songs))

        oldsong = self.__old_value
        for iter_, song in itertools.izip(self.iter_append_many(songs), songs):
            if song is oldsong:
                self.__iter = iter_

        print_d("Done filling model.")

    def remove(self, iter_):
        if self.__iter and self[iter_].path == self[self.__iter].path:
            self.__iter = None
        super(TrackCurrentModel, self).remove(iter_)

    def clear(self):
        self.__iter = None
        super(TrackCurrentModel, self).clear()

    def get(self):
        return list(self.itervalues())

    @property
    def current(self):
        return self.__iter and self.get_value(self.__iter, 0)

    @property
    def current_path(self):
        return self.__iter and self.get_path(self.__iter)

    def __set_current_iter(self, iter_):
        if iter_ == self.__iter:
            return
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
        """Returns the iter to the first occurrence of song in the model
        or None
        """

        # fast path
        if self.current == song:
            return self.current_iter

        # search the rest
        for iter_, value in self.iterrows():
            if value == song:
                return iter_
        return

    def find_all(self, songs):
        """Returns a list of iters for all occurrences of all songs.
        (since a song can be in the model multiple times)
        """

        songs = set(songs)
        found = []
        append = found.append
        for iter_, value in self.iterrows():
            if value in songs:
                append(iter_)
        return found

    def __contains__(self, song):
        return bool(self.find(song))


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
        if isinstance(song, Gtk.TreeIter):
            iter_ = song
        elif song is not None:
            iter_ = self.find(song)

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
        if not self.is_empty():
            self.next()
