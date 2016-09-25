# -*- coding: utf-8 -*-
# Copyright 2006 Joe Wreschnig
#           2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import random

from gi.repository import Gtk, GObject

from quodlibet import config
from quodlibet import qltk
from quodlibet.qltk import Icons
from quodlibet.qltk.x import SymbolicIconImage, RadioMenuItem
from quodlibet.plugins import PluginManager
from quodlibet.util.dprint import print_w, print_d


class Order(object):
    name = "unknown_order"
    display_name = _("Unknown")
    accelerated_name = _("_Unknown")
    replaygain_profiles = ["track"]
    is_shuffle = False
    priority = 100

    def __init__(self):
        """Must have a zero-arg constructor"""
        pass

    def next(self, playlist, iter):
        """Not called directly, but the default implementation of
        `next_explicit` and `next_implicit` both just call this. """
        raise NotImplementedError

    def previous(self, playlist, iter):
        """Not called directly, but the default implementation of
        `previous_explicit` calls this.
        Right now there is no such thing as `previous_implicit`."""
        raise NotImplementedError

    def set(self, playlist, iter):
        """Not called directly, but the default implementations of
        `set_explicit` and `set_implicit` call this. """
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

        If the play order returns `None`,
        no action will be taken by the player."""
        return self.set(playlist, iter)

    def set_implicit(self, playlist, iter):
        """Called when the song is set by a means other than the UI."""
        return self.set(playlist, iter)

    def reset(self, playlist):
        """Called when there is no song ready to prepare for a new order.
        Implementations should reset the state of the current order,
        e.g. forgetting history / clearing pre-cached orders."""
        pass

    def __str__(self):
        """By default there is no interesting state"""
        return "<%s>" % self.display_name


class Reorder(Order):
    """Base class for all `Order`s that potentially reorder the playlist,
    and thus usually identify as a "shuffle" implementation."""
    pass


class Repeat(Order):
    """Repeat, in some way, over a supplied `Order`"""

    def __init__(self, wrapped):
        super(Repeat, self).__init__()
        assert isinstance(wrapped, Order)
        self.wrapped = wrapped

    def next(self, playlist, iter):
        raise NotImplementedError

    def set(self, playlist, iter):
        return self.wrapped.set(playlist, iter)

    def previous(self, playlist, iter):
        return self.wrapped.previous(playlist, iter)

    def reset(self, playlist):
        return self.wrapped.reset(playlist)

    def __str__(self):
        return "<%s ∘ %s>" % (self.display_name, self.wrapped.display_name)


class RepeatSongForever(Repeat):
    name = "repeat_song"
    display_name = _("Repeat track")
    accelerated_name = _("Repeat track")

    def next(self, playlist, iter):
        return iter


class RepeatListForever(Repeat):
    name = "repeat_all"
    display_name = _("Repeat all")
    accelerated_name = _("Repeat all")

    def next(self, playlist, iter):
        next = self.wrapped.next(playlist, iter)
        if next:
            return next
        self.wrapped.reset(playlist)
        return playlist.get_iter_first()


class OrderInOrder(Order):
    """Keep to the order of the supplied playlist"""
    name = "in_order"
    display_name = _("In Order")
    accelerated_name = _("_In Order")
    replaygain_profiles = ["album", "track"]
    priority = 0

    def next(self, playlist, iter):
        if iter is None:
            return playlist.get_iter_first()
        else:
            return playlist.iter_next(iter)

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
                return None


class OrderRemembered(Order):
    """Shared class for all the shuffle modes that keep a memory
    of their previously played songs."""

    def __init__(self):
        super(OrderRemembered, self).__init__()
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


class OrderShuffle(Reorder, OrderRemembered):
    name = "random"
    display_name = _("Random")
    accelerated_name = _("_Random")
    is_shuffle = True
    priority = 1

    def next(self, playlist, iter):
        super(OrderShuffle, self).next(playlist, iter)
        played = set(self._played)
        songs = set(range(len(playlist)))
        remaining = songs.difference(played)

        if remaining:
            return playlist.get_iter((random.choice(list(remaining)),))
        return None


class OrderWeighted(Reorder, OrderRemembered):
    name = "weighted"
    display_name = _("Prefer higher rated")
    accelerated_name = _("Prefer higher rated")
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


class Orders(GObject.Object):
    """
    A minimal list-like container for Order objects
    that signals on changes
    """

    __gsignals__ = {
        'updated': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, initial=None):
        super(Orders, self).__init__()
        self.items = initial or []

    def by_name(self, name):
        if not name:
            return None
        for cls in self.items:
            if cls.name == name:
                return cls
        return None

    def __getitem__(self, y):
        return self.items.__getitem__(y)

    def __len__(self):
        return self.items.__len__()

    def append(self, x):
        self.items.append(x)
        self.emit('updated')

    def remove(self, x):
        self.items.remove(x)
        self.emit('updated')

    def __contains__(self, y):
        return self.items.__contains__(y)

    def sorted(self):
        return sorted(self.items, key=lambda k: (k.priority, k.name))

    def __str__(self):
        return "<%s of %s>" % (type(self).__name__, self.items)


class PluggableOrders(Orders, PluginManager):
    """Registers as a Plugin Handler for various types of `Order` plugins"""
    def __init__(self, orders, base_cls):
        assert issubclass(base_cls, Order)
        super(PluggableOrders, self).__init__(orders)
        self.base_cls = base_cls
        if PluginManager.instance:
            PluginManager.instance.register_handler(self)
        else:
            print_w("No plugin manager found")

    def plugin_handle(self, plugin):
        return issubclass(plugin.cls, self.base_cls)

    def plugin_enable(self, plugin):
        plugin_cls = plugin.cls
        if plugin_cls.name is None:
            plugin_cls.name = plugin.name
        if plugin_cls.display_name is None:
            plugin_cls.display_name = str(plugin.name).capitalize()
        if plugin_cls.accelerated_name is None:
            plugin_cls.accelerated_name = plugin_cls.display_name
        self.append(plugin_cls)

    def plugin_disable(self, plugin):
        self.remove(plugin.cls)

DEFAULT_SHUFFLE_ORDERS = [OrderShuffle, OrderWeighted]
DEFAULT_REPEAT_ORDERS = [RepeatSongForever, RepeatListForever]


class ToggledPlayOrderMenu(Gtk.Box):
    """A toggle button with a menu button.
    Items displayed are all `PlayOrder`

    When the button is toggled, a `toggled` signal gets emitted.
    """

    __gsignals__ = {
        'toggled': (GObject.SignalFlags.RUN_LAST, None, ()),
        'changed': (GObject.SignalFlags.RUN_LAST, None, (object,)),
    }

    def __init__(self, icon_name, orders, current_order, enabled=False,
                 tooltip=None, arrow_down=False):
        """arrow_down -- the direction of the menu and arrow icon"""
        print_d("Building new Toggler set to %r" % enabled)
        assert issubclass(current_order, Order)
        if current_order not in orders:
            raise ValueError("%s is not supported by %s"
                             % (current_order.__name__, orders))

        super(ToggledPlayOrderMenu, self).__init__()
        self.__inhibit = True

        context = self.get_style_context()
        context.add_class(Gtk.STYLE_CLASS_LINKED)

        self._toggle_button = toggle = Gtk.ToggleButton(
            image=SymbolicIconImage(icon_name, Gtk.IconSize.SMALL_TOOLBAR))
        if tooltip:
            toggle.set_tooltip_text(tooltip)
        toggle.set_active(enabled)
        toggle.show_all()
        qltk.remove_padding(toggle)
        toggle.set_size_request(26, 26)
        self.pack_start(toggle, True, True, 0)

        def forward_signal(*args):
            if self.__inhibit:
                print_d("NOT forwarding programmatic toggled signal...")
            else:
                print_d("Forwarding toggled signal...")
                self.emit("toggled")

        toggle.connect("toggled", forward_signal)
        self._toggle_button = toggle

        from quodlibet.qltk.menubutton import MenuButton
        arrow = MenuButton(arrow=True, down=arrow_down)
        arrow.show_all()
        arrow.set_size_request(20, 26)
        qltk.remove_padding(arrow)
        self.pack_start(arrow, True, True, 0)
        self._menu_button = arrow
        self.__current = current_order
        self.__orders = orders
        self.__rebuild_menu()
        self.__inhibit = False

    @property
    def enabled(self):
        """Returns True if toggle button is active"""
        return self._toggle_button.get_active()

    @enabled.setter
    def enabled(self, value):
        """Set button to be active or inactive"""
        print_d("Setting toggle %s to %s" % (self.__orders[0], value))
        self.__inhibit = True
        self._toggle_button.set_active(bool(value))
        self.__inhibit = False

    @property
    def orders(self):
        return self.__orders

    @orders.setter
    def orders(self, values):
        self.__orders = values
        if self.__current not in self.orders:
            self.__current = None
        self.__rebuild_menu()

    @property
    def current(self):
        return self.__current

    @current.setter
    def current(self, value):
        if value not in self.orders:
            raise ValueError(
                "Unknown order %s. Try: %s"
                % (value, ", ".join([o.__name__ for o in self.__orders])))

        self.__current = value
        if not self.__inhibit:
            self.emit('changed', self.__current)

    def set_active_by_name(self, name):
        for cls in self.__orders:
            if cls.name == name:
                self.current = cls
                return
        raise ValueError("Unknown order named \"%s\". Try: %s"
                         % (name, [o.name for o in self.__orders]))

    def set_orders(self, orders):
        self.orders = orders

    def __rebuild_menu(self):

        def toggled_cb(item, order):
            if item.get_active():
                self.current = order

        menu = Gtk.Menu()
        group = None
        for order in self.__orders:
            group = RadioMenuItem(
                label=order.accelerated_name,
                use_underline=True,
                group=group)
            group.set_active(order.name == self.__current)
            group.connect("toggled", toggled_cb, order)
            menu.append(group)
        menu.show_all()
        self._menu_button.set_menu(menu)


class PlayOrderWidget(Gtk.HBox):
    """A combined play order selection widget.
    Whenever something changes the 'changed' signal gets emitted.
    """

    __gsignals__ = {
        'changed': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, model, player):
        super(PlayOrderWidget, self).__init__(spacing=6)
        self.order = None
        self.__inhibit = True
        self.__playlist = model
        self.__player = player

        def create_shuffle(orders):
            shuffle = ToggledPlayOrderMenu(
                Icons.MEDIA_PLAYLIST_SHUFFLE,
                orders=orders,
                current_order=self.__get_shuffle_class(),
                enabled=(config.getboolean("memory", "shuffle", False)),
                tooltip=_("Toggle shuffle mode"))
            shuffle.connect('changed', self.__shuffle_updated)
            shuffle.connect('toggled', self.__shuffle_toggled)
            return shuffle

        self._shuffle_orders = PluggableOrders(DEFAULT_SHUFFLE_ORDERS, Reorder)
        self.__shuffle_widget = create_shuffle(self._shuffle_orders)
        self._shuffle_orders.connect('updated',
                                     self.__shuffle_widget.set_orders)

        def create_repeat(orders):
            repeat = ToggledPlayOrderMenu(
                Icons.MEDIA_PLAYLIST_REPEAT,
                orders=orders,
                current_order=self.__get_repeat_class(),
                enabled=config.getboolean("memory", "repeat", False),
                tooltip=_("Toggle repeat mode"))
            repeat.connect('changed', self.__repeat_updated)
            repeat.connect('toggled', self.__repeat_toggled)
            return repeat
        self._repeat_orders = PluggableOrders(DEFAULT_REPEAT_ORDERS, Repeat)
        self.__repeat_widget = create_repeat(self._repeat_orders)
        self._repeat_orders.connect('updated', self.__repeat_widget.set_orders)

        self.__compose_order()
        self.pack_start(self.__shuffle_widget, False, True, 0)
        self.pack_start(self.__repeat_widget, False, True, 0)
        self.__inhibit = False

    @property
    def shuffler(self):
        return self.__shuffle_widget.current

    @shuffler.setter
    def shuffler(self, cls):
        assert issubclass(cls, Reorder)
        self.__shuffle_widget.current = cls

    @property
    def repeater(self):
        return self.__repeat_widget.current

    @repeater.setter
    def repeater(self, cls):
        assert issubclass(cls, Repeat)
        self.__repeat_widget.current = cls

    @property
    def shuffled(self):
        return self.__shuffle_widget.enabled

    @shuffled.setter
    def shuffled(self, enabled):
        self.__shuffle_widget.enabled = bool(enabled)
        self.__compose_order()

    @property
    def repeated(self):
        return self.__repeat_widget.enabled

    @repeated.setter
    def repeated(self, enabled):
        self.__repeat_widget.enabled = bool(enabled)
        self.__compose_order()

    def __repeat_updated(self, widget, repeat_cls):
        if self.__inhibit:
            return
        print_d("New repeat mode: %s" % repeat_cls.name)
        config.set("memory", "repeat_mode", repeat_cls.name)
        self.__compose_order()

    def __shuffle_updated(self, widget, shuffle_cls):
        if self.__inhibit:
            return
        print_d("New shuffle mode: %s" % shuffle_cls.name)
        config.set("memory", "shuffle_mode", shuffle_cls.name)
        self.__compose_order()

    def __shuffle_toggled(self, widget):
        if self.__inhibit:
            return
        print_d("Shuffle toggled")
        config.set("memory", "shuffle", widget.enabled)
        self.__compose_order()

    def __repeat_toggled(self, widget):
        if self.__inhibit:
            return
        print_d("Repeat toggled")
        config.set("memory", "repeat", widget.enabled)
        self.__compose_order()

    def __compose_order(self):
        old_order = self.order
        repeat_cls = self.__get_repeat_class()
        shuffle_cls = self.__get_shuffle_class()
        shuffler = (shuffle_cls() if self.shuffled else OrderInOrder())
        self.order = repeat_cls(shuffler) if self.repeated else shuffler
        print_d("Updating %s order to %s"
                % (type(self.__playlist).__name__, self.order))
        self.__playlist.order = self.order
        self.__player.replaygain_profiles[2] = shuffler.replaygain_profiles
        self.__player.reset_replaygain()
        if self.order != old_order:
            self.emit('changed')

    def __get_shuffle_class(self):
        name = config.get("memory", "shuffle_mode", None)
        return self._shuffle_orders.by_name(name) or OrderShuffle

    def __get_repeat_class(self):
        name = config.get("memory", "repeat_mode", None)
        return self._repeat_orders.by_name(name) or RepeatSongForever
