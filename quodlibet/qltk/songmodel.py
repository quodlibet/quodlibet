# Copyright 2012 Christoph Reiter
#        2016-23 Nick Boultbee
#      2018-2019 Fredrik Strupe
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from typing import Any
from collections.abc import Iterable, Sequence

from gi.repository import Gtk

from quodlibet.order import Order
from quodlibet.qltk.playorder import OrderInOrder
from quodlibet.qltk.models import ObjectStore
from quodlibet.util import print_d
from quodlibet import config


class PlaylistMux:
    """Provides the PlaylistModel interface combining the song list model and
    the queue one.

    If no longer needed, call destroy().
    """

    def __init__(self, player, q, pl):
        self.q = q
        self.pl = pl
        self._id = player.connect("song-started", self.__song_started)
        self._player = player

    def destroy(self):
        self._player.disconnect(self._id)

    def __song_started(self, player, song):
        if song is not None and self.q.sourced:
            iter = self.q.find(song)
            keep_song = config.getboolean("memory", "queue_keep_songs", False)
            if iter and not keep_song:
                self.q.remove(iter)
                # we don't call _check_sourced here since we want the queue
                # to stay sourced even if no current song is left

    @property
    def current(self):
        """The current song or None"""

        if self.q.current is not None:
            return self.q.current
        return self.pl.current

    def _check_sourced(self):
        if self.q.current is not None:
            self.q.sourced = True
            self.pl.sourced = False
        else:
            self.q.sourced = False
            self.pl.sourced = True

    def next(self):
        """Switch to the next song"""

        keep_songs = config.getboolean("memory", "queue_keep_songs", False)
        q_disable = config.getboolean("memory", "queue_disable", False)

        if self.q.is_empty() or q_disable or (keep_songs and not self.q.sourced):
            self.pl.next()
            if q_disable and self.q.sourced:
                # The go_to is to make sure the playlist begins playing
                # when the queue is disabled while being sourced
                self.go_to(self.pl.current)
        else:
            self.q.next()
        self._check_sourced()

    def next_ended(self):
        """Switch to the next song (action comes from the user)"""

        keep_songs = config.getboolean("memory", "queue_keep_songs", False)
        q_disable = config.getboolean("memory", "queue_disable", False)

        if self.q.is_empty() or q_disable or (keep_songs and not self.q.sourced):
            self.pl.next_ended()
            if q_disable and self.q.sourced:
                self.go_to(self.pl.current)
        else:
            self.q.next_ended()
        self._check_sourced()

    def previous(self):
        """Go to the previous song"""

        keep_songs = config.getboolean("memory", "queue_keep_songs", False)
        q_disable = config.getboolean("memory", "queue_disable", False)

        if q_disable or self.pl.sourced or not keep_songs:
            self.pl.previous()
            if q_disable and self.q.sourced:
                self.go_to(self.pl.current)
        else:
            self.q.previous()
        self._check_sourced()

    def go_to(self, song, explicit=False, source=None):
        """Switch the current active song to song.

        song can be an Gtk.TreeIter or AudioFile.
        explicit should be True of the action comes from the user.
        source should be the right PlaylistModel in case song is an iter.
        """

        main, other = self.pl, self.q
        if source is not None:
            assert source in (self.pl, self.q)
            if source is self.q:
                main, other = other, main
        res = main.go_to(song, explicit)
        if res is not None or not explicit:
            other.go_to(None)
        self._check_sourced()
        return res

    def reset(self):
        """Switch to the first song"""

        self.q.go_to(None)
        self.pl.reset()
        self._check_sourced()

    def enqueue(self, songs):
        """Append the songs to the queue model"""

        self.q.append_many(songs)

    def unqueue(self, songs):
        """Remove all occurrences of all passed songs in the queue"""

        q = self.q
        for iter_ in q.find_all(songs):
            q.remove(iter_)


class TrackCurrentModel(ObjectStore):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__iter = None

    last_current: Any | None = None
    """The last valid current song"""

    def set(self, songs: Sequence[Any]):
        """Clear the model and add the passed songs"""

        print_d("Filling view model with %d songs." % len(songs))
        self.clear()
        self.__iter = None

        oldsong = self.last_current
        for iter_, song in zip(self.iter_append_many(songs), songs, strict=False):
            if song is oldsong:
                self.__iter = iter_

    def get(self) -> list[Any]:
        """A list of all contained songs"""

        return list(self.itervalues())

    @property
    def current(self) -> Any | None:
        """The current song or None"""

        return self.__iter and self.get_value(self.__iter, 0)

    @property
    def current_path(self):
        """The Gtk.TreePath of the current song or None"""

        return self.__iter and self.get_path(self.__iter)

    @property
    def current_iter(self):
        """The Gtk.TreeIter of the current song or None"""

        return self.__iter

    @current_iter.setter
    def current_iter(self, iter_):
        if iter_ == self.__iter:
            return
        # emit a row-changed for the previous and the new iter after it is set
        # so that the currentcolumn icon gets updated on song changes
        for it in filter(None, (self.__iter, iter_)):
            self.row_changed(self.get_path(it), it)
        self.__iter = iter_
        self.last_current = self.current

    def find(self, song: Any):
        """Returns the iter to the first occurrence of song in the model
        or None if it wasn't found.
        """

        # fast path
        if self.current == song:
            return self.current_iter

        # search the rest
        for iter_, value in self.iterrows():
            if value == song:
                return iter_
        return None

    def find_all(self, songs: Iterable[Any]):
        """Returns a list of iters for all occurrences of all songs.
        (since a song can be in the model multiple times)
        """

        songs = set(songs)
        return [iter_ for iter_, value in self.iterrows() if value in songs]

    def remove(self, iter_):
        if self.__iter and self[iter_].path == self[self.__iter].path:
            self.__iter = None
        super().remove(iter_)

    def clear(self):
        self.__iter = None
        super().clear()

    def __contains__(self, song):
        return bool(self.find(song))


class PlaylistModel(TrackCurrentModel):
    """A play list model for song lists"""

    order: Order
    """The active play order"""

    sourced = False
    """True in case this model is the source of the currently playing song"""

    def __init__(self, order_cls: type[Order] = OrderInOrder):
        super().__init__(object)
        self.order = order_cls()

    def next(self):
        """Switch to the next song"""

        iter_ = self.current_iter
        print_d(f"Using {self.order}.next_explicit() to get next song")
        self.current_iter = self.order.next_explicit(self, iter_)

    def next_ended(self):
        """Switch to the next song (action comes from the user)"""

        iter_ = self.current_iter
        print_d(f"Using {self.order}.next_implicit() to get next song")
        self.current_iter = self.order.next_implicit(self, iter_)

    def previous(self):
        """Go to the previous song"""

        iter_ = self.current_iter
        self.current_iter = self.order.previous_explicit(self, iter_)

    def go_to(self, song_or_iter, explicit=False, source=None):
        """Switch the current active song to song.

        song can be an Gtk.TreeIter or AudioFile.
        explicit should be True of the action comes from the user.
        source should be this model or None.
        """

        assert source is None or source is self

        iter_ = None
        if isinstance(song_or_iter, Gtk.TreeIter):
            iter_ = song_or_iter
        elif song_or_iter is not None:
            # We were told to go to a song that was valid but couldn't find it.
            # Set it as last current so it gets set current when we find it in
            # the future.
            self.last_current = song_or_iter
            iter_ = self.find(song_or_iter)

        if explicit:
            self.current_iter = self.order.set_explicit(self, iter_)
        else:
            self.current_iter = self.order.set_implicit(self, iter_)

        return self.current_iter

    def set(self, songs: Sequence[Any]):
        """Clear the model and add the passed songs"""

        self.order.reset(self)
        super().set(songs)

    def remove(self, iter_):
        self.order.reset(self)
        super().remove(iter_)

    def clear(self):
        self.order.reset(self)
        super().clear()

    def reset(self):
        """Switch to the first song"""

        self.go_to(None)
        self.order.reset(self)
        if not self.is_empty():
            self.next()
