# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import random

import gtk

from quodlibet import config

class Order(object):
    name = "unknown_order"
    display_name = _("Unknown")
    accelerated_name = _("_Unknown")
    replaygain_profiles = ["track"]
    priority = 100

    def __init__(self, playlist):
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

    # Called when a song ends passively, e.g. it plays through.
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
    replaygain_profiles = ["album", "track"]
    priority = 0

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

class OrderRemembered(Order):
    # Shared class for all the shuffle modes that keep a memory
    # of their previously played songs.

    def __init__(self, playlist):
        super(OrderRemembered, self).__init__(playlist)
        self._played = []

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

    def reset(self, playlist):
        del(self._played[:])

class OrderShuffle(OrderRemembered):
    name = "shuffle"
    display_name = _("Shuffle")
    accelerated_name = _("_Shuffle")
    priority = 1

    def next(self, playlist, iter):
        super(OrderShuffle, self).next(playlist, iter)
        played = set(self._played)
        songs = set(range(len(playlist)))
        remaining = songs.difference(played)

        if remaining:
            return playlist.get_iter((random.choice(list(remaining)),))
        elif playlist.repeat and not playlist.is_empty():
            del(self._played[:])
            return playlist.get_iter((random.choice(list(songs)),))
        else:
            del(self._played[:])
            return None

class OrderWeighted(OrderRemembered):
    name = "Weighted"
    display_name = _("Weighted")
    accelerated_name = _("_Weighted")
    priority = 2

    def next(self, playlist, iter):
        super(OrderShuffle, self).next(playlist, iter)
        songs = playlist.get()
        max_score = sum([song.get('~#rating', 2) for song in songs])
        choice = random.random() * max_score
        current = 0.0
        for i, song in enumerate(songs):
            current += song.get("~#rating", 2)
            if current >= choice:
                return playlist.get_iter((i,))
        else:
            return playlist.get_iter_first()

class OrderOneSong(OrderInOrder):
    name = "onesong"
    display_name = _("One Song")
    accelerated_name = _("_One Song")
    priority = 3

    def next_implicit(self, playlist, iter):
        if playlist.repeat:
            return iter
        else:
            return None

ORDERS = [OrderInOrder, OrderShuffle, OrderWeighted, OrderOneSong]

ORDERS.sort(lambda K1, K2:
            cmp(K1.priority, K2.priority) or cmp(K1.name, K2.name))

class PlayOrder(gtk.ComboBox):
    def __init__(self, model, player):
        super(PlayOrder, self).__init__(gtk.ListStore(str))
        cell = gtk.CellRendererText()
        self.pack_start(cell, True)
        self.add_attribute(cell, 'text', 0)
        for order in ORDERS:
            self.append_text(order.display_name)
        self.connect_object('changed', self.__changed_order, model, player)
        self.set_active(config.get("memory", "order"))

    def set_active(self, value):
        try: value = ORDERS.index(value)
        except ValueError:
            for i, Order in enumerate(ORDERS):
                if Order.name == value:
                    value = i
                    break
        try: value = int(value)
        except ValueError: value = 0
        super(PlayOrder, self).set_active(value)

    def get_active_name(self):
        return ORDERS[self.get_active()].name

    def __changed_order(self, model, player):
        Order = ORDERS[self.get_active()]
        model.order = Order(model)
        config.set("memory", "order", Order.name)
        player.replaygain_profiles[1] = Order.replaygain_profiles
        player.volume = player.volume
