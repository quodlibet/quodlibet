# Copyright 2006 Joe Wreschnig
#        2016-23 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from typing import Any

from gi.repository import Gtk

from quodlibet import _, print_d


class Order:
    """Base class for all play orders

    In all methods:
        `playlist` is a GTK+ `ListStore` containing at least an `AudioFile`
                   as the first element in each row
                   (in the future there may be more elements per row).

        `iter`     is a `GtkTreeIter` for the song that just finished, if any.
                   If the song is not in the list, this iter will be `None`.
    """

    name: str | None = "unknown_order"
    """The name by which this order is known"""

    display_name = _("Unknown")
    """The (translated) display name"""

    accelerated_name = _("_Unknown")
    """The (translated) display name with (optional) accelerators"""

    replaygain_profiles = ["track"]
    """The ReplayGain mode(s) to use with this order.
    Shuffled ones typically prefer track modes"""

    priority = 100
    """The priority relative to other orders of its type.
    Larger numbers typically appear lower in lists."""

    def __init__(self):
        """Must have a zero-arg constructor"""

    def next(self, playlist, iter):
        """Not called directly, but the default implementation of
        `next_explicit` and `next_implicit` both just call this."""
        raise NotImplementedError

    def previous(self, playlist, iter):
        """Not called directly, but the default implementation of
        `previous_explicit` calls this.
        Right now there is no such thing as `previous_implicit`."""
        raise NotImplementedError

    def set(self, playlist, iter):
        """Not called directly, but the default implementations of
        `set_explicit` and `set_implicit` call this."""
        return iter

    def next_explicit(self, playlist, iter):
        """Not called directly, but the default implementations of
        `set_explicit` and `set_implicit` call this."""
        return self.next(playlist, iter)

    def next_implicit(self, playlist, iter):
        """Called when a song ends passively, e.g. it plays through."""
        return self.next(playlist, iter)

    def previous_explicit(self, playlist, iter):
        """Called when the user presses a "Previous" button."""
        return self.previous(playlist, iter)

    def set_explicit(self, playlist, iter):
        """Called when the user manually selects a song (at `iter`).
        If desired the play order can override that, or just
        log it and return the iter again.
        Note that playlist.current_iter is the current iter, if any.

        If the play order returns `None`,
        no action will be taken by the player.
        """
        return self.set(playlist, iter)

    def set_implicit(self, playlist, iter):
        """Called when the song is set by a means other than the UI."""
        return self.set(playlist, iter)

    def reset(self, playlist):
        """Called when there is no song ready to prepare for a new order.
        Implementations should reset the state of the current order,
        e.g. forgetting history / clearing pre-cached orders."""

    def __str__(self):
        """By default there is no interesting state"""
        return f"<{self.display_name}>"


class OrderRemembered(Order):
    """Shared class for all the shuffle modes that keep a memory
    of their previously played songs."""

    _played: list[Gtk.TreeIter]

    def __init__(self):
        super().__init__()
        self._played = []

    def next(self, playlist, iter):
        if iter is not None:
            self._played.append(iter)

    def previous(self, playlist, iter):
        if self._played:
            return self._played.pop()
        return None

    def set(self, playlist, iter):
        if iter is not None:
            self._played.append(iter)
        return iter

    def reset(self, playlist):
        del self._played[:]

    def remaining(self, playlist) -> dict[int, Any]:
        """Gets a map of all song indices to their song from the `playlist`
        that haven't yet been played"""

        def get_index(iter) -> int:
            path = playlist.get_path(iter)
            return path.get_indices()[0]

        played = set(map(get_index, self._played))
        print_d("Played %d of %d song(s)" % (len(self._played), len(playlist)))
        remaining = ((get_index(iter), value) for iter, value in playlist.iterrows())
        return {index: song for (index, song) in remaining if index not in played}


class OrderInOrder(Order):
    """Keep to the order of the supplied playlist"""

    name: str | None = "in_order"
    display_name = _("In Order")
    accelerated_name = _("_In Order")
    replaygain_profiles = ["album", "track"]
    priority = 0

    def next(self, playlist, iter):
        if iter is None:
            return playlist.get_iter_first()
        return playlist.iter_next(iter)

    def previous(self, playlist, iter):
        if len(playlist) == 0:
            return None
        if iter is None:
            return playlist[(len(playlist) - 1,)].iter
        path = max(1, playlist.get_path(iter).get_indices()[0])
        try:
            return playlist.get_iter((path - 1,))
        except ValueError:
            return None
