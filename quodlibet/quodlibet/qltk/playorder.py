# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gtk

from quodlibet import config

_ORDERS = ["inorder", "shuffle", "weighted", "onesong"]
_TRANS = {"inorder": _("In Order"),
          "shuffle": _("Shuffle"),
          "weighted": _("Weighted"),
          "onesong": _("One Song")
          }

# Canonical accelerated versions, in case we need them (e.g. the tray
# icon uses them right now).
_("_Shuffle")
_("_Weighted")

class Order(object):
    name = "unknown_order"
    display_name = _("Unknown")

    def __init__(self, playlist, iter):
        self.playlist = playlist

    # Not called directly, but the default implementation of
    # next_explicit and next_implicit both just call this.
    def next(self, playlist, iter):
        raise NotImplementedError

    # Not called directly, but the default implementation of
    # previous_explicit calls this. Right now there is no such thing
    # as previous_implicit.
    def previous(self, playlist, iter):
        raise NotImplementedError

    # Not called directly, but the default implementation of
    # set_explicit calls this. Right now there is no such thing as
    # set_implicit.
    def set(self, playlist, iter):
        return iter

    # Called when the user presses a "Next" button.
    def next_explicit(self, playlist, iter):
        return self.next(playlist, iter)

    # Called when a song ends passively, e.g. it runs out of time, or
    # the file could not be found. By default, do the same thing as an
    # explicit end.
    def next_implicit(self, playlist, iter):
        return self.next(playlist, iter)

    # Called when the user presses a "Previous" button.
    def previous_explicit(self, playlist, iter):
        return self.previous(playlist, iter)

    # Called when the user manually selects a song (at iter).
    # If desired the play order can override that, or just
    # log it and return the iter again.
    def set_explicit(self, playlist, iter):
        return self.set(playlist, iter)

    def reset(self, playlist):
        pass

class OrderInOrder(Order):
    name = "inorder"
    display_name = _("In Order")
    accelerated_name = _("_In Order")

    def next(self, playlist, iter):
        if iter is None:
            return playlist.get_iter_first()
        else:
            next = playlist.iter_next(iter)
            if next is None and playlist.repeat:
                next = self.get_iter_first()
            return next

    def previous(self, playlist, iter):
        if len(playlist) == 0:
            return None
        elif iter is None:
            return playlist[(len(playlist) - 1,)].iter
        else:
            path = playlist.get_path(iter)[0]
            try: return playlist.get_iter((path - 1,))
            except ValueError:
                if playlist.repeat:
                    return playlist[(len(playlist) - 1,)].iter
        return None

class OrderOneSong(OrderInOrder):
    name = "onesong"
    display_name = _("One Song")
    accelerated_name = _("_One Song")

    def next_implicit(self, playlist, iter):
        if playlist.repeat:
            return iter
        else:
            return None

class OrderRemembered(Order):
    # Shared class for all the shuffle modes that keep a memory
    # of their previously played songs.

    # A list of previously played paths.
    _played = []

    def next(self, playlist, iter):
        if iter is not None:
            self._played.append(playlist.get_path(iter)[0])

    def previous(self, playlist, iter):
        try: path = self._played.pop()
        except IndexError: return None
        else: return playlist.get_iter(path)

    def set(self, playlist, iter):
        if iter is not None:
            self._played.append(playlist.get_path(iter)[0])
        return iter

    def reset(self):
        del(self.played[:])

class PlayOrder(gtk.ComboBox):
    def __init__(self, model, player):
        super(PlayOrder, self).__init__(gtk.ListStore(str))
        cell = gtk.CellRendererText()
        self.pack_start(cell, True)
        self.add_attribute(cell, 'text', 0)
        for order in _ORDERS: self.append_text(_TRANS[order])
        self.connect_object('changed', self.__changed_order, model, player)
        self.set_active(config.get("memory", "order"))

    def set_active(self, value):
        try: super(PlayOrder, self).set_active(_ORDERS.index(value))
        except: super(PlayOrder, self).set_active(int(value))

    def get_active_name(self):
        return _ORDERS[self.get_active()]

    def __changed_order(self, model, player):
        model.order = self.get_active()
        config.set("memory", "order", _ORDERS[self.get_active()])

        if model.order == 0:
            player.replaygain_profiles[1] = ["album", "track"]
        else:
            player.replaygain_profiles[1] = ["track"]
        player.volume = player.volume
