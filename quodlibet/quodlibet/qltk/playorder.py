# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import random

from gi.repository import Gtk, GObject

from quodlibet import config
from quodlibet import qltk
from quodlibet.qltk.x import SymbolicIconImage, RadioMenuItem
from quodlibet.plugins import PluginManager, PluginHandler


class Order(object):
    name = "unknown_order"
    display_name = _("Unknown")
    accelerated_name = _("_Unknown")
    replaygain_profiles = ["track"]
    is_shuffle = False
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

    # Not called directly, but the default implementations of
    # set_explicit and set_implicit call this.
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
    # log it and return the iter again. If the play order returns
    # None, no action will be taken by the player.
    def set_explicit(self, playlist, iter):
        return self.set(playlist, iter)

    # Called when the song is set by a means other than the UI.
    def set_implicit(self, playlist, iter):
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
                next = playlist.get_iter_first()
            return next

    def previous(self, playlist, iter):
        if len(playlist) == 0:
            return None
        elif iter is None:
            return playlist[(len(playlist) - 1,)].iter
        else:
            path = max(1, playlist.get_path(iter).get_indices()[0])
            try:
                return playlist.get_iter((path - 1,))
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
            self._played.append(playlist.get_path(iter).get_indices()[0])

    def previous(self, playlist, iter):
        try:
            path = self._played.pop()
        except IndexError:
            return None
        else:
            return playlist.get_iter(path)

    def set(self, playlist, iter):
        if iter is not None:
            self._played.append(playlist.get_path(iter).get_indices()[0])
        return iter

    def reset(self, playlist):
        del(self._played[:])


class OrderShuffle(OrderRemembered):
    name = "shuffle"
    display_name = _("Shuffle")
    accelerated_name = _("_Shuffle")
    is_shuffle = True
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
    name = "weighted"
    display_name = _("Weighted")
    accelerated_name = _("_Weighted")
    is_shuffle = True
    priority = 2

    def next(self, playlist, iter):
        super(OrderWeighted, self).next(playlist, iter)
        songs = playlist.get()
        max_score = sum([song('~#rating') for song in songs])
        choice = random.random() * max_score
        current = 0.0
        for i, song in enumerate(songs):
            current += song("~#rating")
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

ORDERS = []


def set_orders(orders):
    ORDERS[:] = [OrderInOrder, OrderShuffle, OrderWeighted, OrderOneSong]
    ORDERS.extend(orders)
    ORDERS.sort(lambda K1, K2:
                cmp(K1.priority, K2.priority) or cmp(K1.name, K2.name))
set_orders([])


class ShuffleButton(Gtk.Box):
    """A shuffle toggle button + a menu button.

    In case the shuffle button gets toggled, 'toggled' gets emitted.
    """

    __gsignals__ = {
        'toggled': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, arrow_down=False):
        """arrow_down -- the direction of the menu and arrow icon"""

        super(ShuffleButton, self).__init__()

        context = self.get_style_context()
        context.add_class(Gtk.STYLE_CLASS_LINKED)

        # shuffle button
        b = Gtk.ToggleButton(image=SymbolicIconImage(
            "media-playlist-shuffle", Gtk.IconSize.SMALL_TOOLBAR))
        b.show_all()
        qltk.add_css(b, """
            * {
                padding: 0px;
            }
        """)
        b.set_size_request(26, 26)
        self.pack_start(b, True, True, 0)

        def forward_signal(*args):
            self.emit("toggled")

        b.connect("toggled", forward_signal)
        self._toggle_button = b

        # arrow
        from quodlibet.qltk.menubutton import MenuButton
        b = MenuButton(arrow=True, down=arrow_down)
        b.show_all()
        b.set_size_request(20, 26)
        qltk.add_css(b, """
            * {
                padding: 0px;
            }
        """)
        self.pack_start(b, True, True, 0)
        self._menu_button = b

    def set_active(self, value):
        """Set if shuffle is active"""

        self._toggle_button.set_active(value)

    def get_active(self):
        """Get if shuffle is active"""

        return self._toggle_button.get_active()

    def set_menu(self, menu):
        """Replace the current menu with a new one"""

        self._menu_button.set_menu(menu)


class PlayOrder(Gtk.Box, PluginHandler):
    """A play order selection widget.

    Whenever something changes the 'changed' signal gets emitted.

    TODO: split up in UI and management part
    """

    __gsignals__ = {
        'changed': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, model, player):
        super(PlayOrder, self).__init__()

        self._model = model
        self._player = player
        self._plugins = []
        self._inhibit_save = False

        self._shuffle = shuffle = ShuffleButton()
        self.pack_start(shuffle, True, True, 0)

        if PluginManager.instance:
            PluginManager.instance.register_handler(self)

        self._set_order(
            self._get_order(config.getboolean("memory", "shuffle")))
        shuffle.connect("toggled", self._random_toggle)

    def set_shuffle(self, value):
        """Set shuffle, will change the order accordingly"""

        self._shuffle.set_active(value)

    def get_shuffle(self):
        """If the active order is a shuffle based one"""

        return self._shuffle.get_active()

    def set_active_by_name(self, name):
        """Set the active play order via the order name.

        Raises ValueError if not found.
        """

        for order in ORDERS:
            if order.name == name:
                self._set_order(order)
                return
        raise ValueError("order %r not available" % name)

    def set_active_by_index(self, index):
        """Set by index number in global order list.

        Raises IndexError
        """

        self._set_order(ORDERS[index])

    def get_active(self):
        """Get the active order"""

        return self._get_order(self.get_shuffle())

    def get_active_name(self):
        """Get the identifier name for the active play order"""

        return self.get_active().name

    def _get_order(self, shuffle):
        """Get the active order for shuffle/inorder mode"""

        first_matching = None
        if shuffle:
            name = config.get("memory", "order_shuffle")
        else:
            name = config.get("memory", "order")
        for order in ORDERS:
            if order.is_shuffle == shuffle:
                first_matching = first_matching or order
                if order.name == name:
                    return order
        return first_matching

    def _set_order(self, order_cls):
        """Set shuffle and order based on the passed class"""

        self._model.order = order_cls(self._model)
        is_shuffle = order_cls.is_shuffle

        if not self._inhibit_save:
            config.set("memory", "shuffle", is_shuffle)
            if is_shuffle:
                config.set("memory", "order_shuffle", order_cls.name)
            else:
                config.set("memory", "order", order_cls.name)
        self.set_shuffle(is_shuffle)
        self._refresh_menu()

        self._player.replaygain_profiles[2] = order_cls.replaygain_profiles
        self._player.volume = self._player.volume
        self.emit("changed")

    def _refresh_menu(self):
        is_shuffle = self._shuffle.get_active()

        def toggled_cb(item, order):
            if item.get_active():
                self._set_order(order)

        active_order = self._get_order(is_shuffle)

        menu = Gtk.Menu()
        group = None
        for order in ORDERS:
            if order.is_shuffle == is_shuffle:
                group = RadioMenuItem(
                    label=order.accelerated_name,
                    use_underline=True,
                    group=group)
                group.set_active(order == active_order)
                group.connect("toggled", toggled_cb, order)
                menu.append(group)
        menu.show_all()
        self._shuffle.set_menu(menu)

    def _random_toggle(self, button):
        self._set_order(self._get_order(button.get_active()))

    def plugin_handle(self, plugin):
        from quodlibet.plugins.playorder import PlayOrderPlugin
        return issubclass(plugin.cls, PlayOrderPlugin)

    def plugin_enable(self, plugin):
        plugin_cls = plugin.cls
        if plugin_cls.name is None:
            plugin_cls.name = plugin.name
        if plugin_cls.display_name is None:
            plugin_cls.display_name = plugin.name
        if plugin_cls.accelerated_name is None:
            plugin_cls.accelerated_name = plugin_cls.display_name

        self._plugins.append(plugin_cls)
        set_orders(self._plugins)
        self._refresh_menu()

    def plugin_disable(self, plugin):
        order = plugin.cls
        self._plugins.remove(order)
        set_orders(self._plugins)

        # Don't safe changes from plugin changes
        # so that disables on shutdown don't change the config.
        self._inhibit_save = True
        self._set_order(self._get_order(self.get_shuffle()))
        self._inhibit_save = False
