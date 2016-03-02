# -*- coding: utf-8 -*-
# Copyright 2005 Joe Wreschnig, Michael Urman
#           2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, Gdk

from quodlibet.qltk import get_top_parent, is_wayland
from quodlibet.qltk.x import Align


def window_grab_and_map(window, mask):
    """Returns a list of devices that have a grab or an empty list if
    something failed.

    If somethings failed the window will be hidden.
    """

    device = Gtk.get_current_event_device()
    event_time = Gtk.get_current_event_time()
    if not device:
        return []

    # On wayland we need to grab before mapping and on X11 and everywhere else
    # we can grab after we are mapped
    if not is_wayland():
        window.show()
    else:
        window.realize()

    Gtk.device_grab_add(window, device, True)

    status = device.grab(
        window.get_window(), Gdk.GrabOwnership.WINDOW, True,
        mask, None, event_time)

    if status != Gdk.GrabStatus.SUCCESS:
        Gtk.device_grab_remove(window, device)
        window.hide()
        return []

    associated_device = device.get_associated_device()
    if associated_device is None:
        if is_wayland():
            window.show()
        return [device]

    Gtk.device_grab_add(window, associated_device, True)

    status = associated_device.grab(
        window.get_window(), Gdk.GrabOwnership.WINDOW, True,
        mask, None, event_time)

    if status != Gdk.GrabStatus.SUCCESS:
        Gtk.device_grab_remove(window, associated_device)
        Gtk.device_grab_remove(window, device)
        device.ungrab(event_time)
        window.hide()
        return []

    if is_wayland():
        window.show()

    return [device, associated_device]


def window_ungrab_and_unmap(window, devices):
    """Takes the result of window_grab_and_map() and removes the grabs"""

    event_time = Gtk.get_current_event_time()
    for device in devices:
        Gtk.device_grab_remove(window, device)
        device.ungrab(event_time)
    window.hide()
    #gtk3.8 bug: https://bugzilla.gnome.org/show_bug.cgi?id=700185
    window.unrealize()


class _PopupSlider(Gtk.Button):
    # Based on the Rhythmbox volume control button; thanks to Colin Walters,
    # Richard Hult, Michael Fulbright, Miguel de Icaza, and Federico Mena.

    def __init__(self, child=None, adj=None):
        super(_PopupSlider, self).__init__()
        if child:
            self.add(child)
        self.connect('clicked', self.__clicked)

        self._disable_slider = False
        self.__grabbed = []

        window = self.__window = Gtk.Window(type=Gtk.WindowType.POPUP)
        self.__adj = adj or self._adj

        frame = Gtk.Frame()
        frame.set_border_width(0)
        frame.set_shadow_type(Gtk.ShadowType.OUT)

        self.add_events(Gdk.EventMask.SCROLL_MASK)

        hscale = Gtk.Scale(adjustment=self.__adj)
        hscale.set_orientation(self.ORIENTATION)
        window.connect('button-press-event', self.__button)
        window.connect('key-press-event', self.__key)
        hscale.set_draw_value(False)
        self.scale = hscale
        window.add(frame)
        self._box = Gtk.Box(orientation=self.ORIENTATION)
        self._box.add(hscale)
        frame.add(self._box)
        self.connect('scroll-event', self.__scroll, hscale)

        self.connect("destroy", self.__destroy)

        # forward scroll event to the button
        def foward_scroll(scale, event):
            self.emit('scroll-event', event.copy())
        window.connect('scroll-event', foward_scroll)

        # ignore scroll events on the scale, the window handles it instead
        self.scale.connect('scroll-event', lambda *x: True)

        # handle all unhandled button events on the scale
        # so only events not on the scale hide the window
        def handle_all(scale, event):
            return True
        self.scale.connect_after('button-press-event', handle_all)
        self.scale.connect_after('button-release-event', handle_all)

        self.set_slider_length(200)

        if child:
            self.get_child().show_all()

    def __destroy(self, *args):
        self.__window.destroy()
        self.__window = None

    def set_slider_disabled(self, disable):
        """Hide the slider and don't allow showing it again until it is
        enabled again
        """

        self._disable_slider = disable
        if disable:
            self.__popup_hide()

    def set_slider_length(self, length):
        if self.ORIENTATION == Gtk.Orientation.HORIZONTAL:
            self.scale.set_size_request(length, -1)
        else:
            self.scale.set_size_request(-1, length)

        # force a window resize..
        self.__window.resize(1, 1)

    def set_slider_widget(self, widget):
        self._box.pack_start(
            Align(widget, border=6, left=-3), False, True, 0)

    def _move_to(self, x, y, w, h, ww, wh, pad=3):
        raise NotImplementedError

    def __clicked(self, button):
        if self.__window.get_property('visible'):
            return

        if self._disable_slider:
            return

        if self.__grabbed:
            self.__popup_hide()

        window = self.__window
        frame = window.get_child()

        frame.show_all()
        window.size_request()

        dummy, x, y = self.get_window().get_origin()
        x, y = self.translate_coordinates(self.get_toplevel(), x, y)[:2]

        button_alloc = self.get_allocation()
        w, h = button_alloc.width, button_alloc.height

        ww, wh = window.get_size()
        sx, sy = self._move_to(x, y, w, h, ww, wh, pad=3)
        window.set_transient_for(get_top_parent(self))
        window.move(sx, sy)
        # this type hint tells the wayland backend to create a popup
        window.set_type_hint(Gdk.WindowTypeHint.DROPDOWN_MENU)

        self.__grabbed = window_grab_and_map(
            window,
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.BUTTON_MOTION_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.SCROLL_MASK)

    def __scroll(self, widget, ev, hscale):
        adj = self.__adj
        v = hscale.get_value()
        if ev.direction in self.UP:
            v += adj.props.step_increment
        elif ev.direction in self.DOWN:
            v -= adj.props.step_increment
        else:
            # newer Gdk.ScrollDirection.SMOOTH
            return
        v = min(adj.props.upper, max(adj.props.lower, v))
        hscale.set_value(v)

    def __button(self, widget, ev):
        self.__popup_hide()

    def __key(self, hscale, ev):
        if ev.string in ["\n", "\r", " ", "\x1b"]:  # enter, space, escape
            self.__popup_hide()

    def __popup_hide(self):
        window_ungrab_and_unmap(self.__window, self.__grabbed)
        del self.__grabbed[:]


class HSlider(_PopupSlider):
    ORIENTATION = Gtk.Orientation.HORIZONTAL
    _adj = Gtk.Adjustment.new(0, 0, 0, 3, 15, 0)
    UP = [Gdk.ScrollDirection.DOWN, Gdk.ScrollDirection.RIGHT]
    DOWN = [Gdk.ScrollDirection.UP, Gdk.ScrollDirection.LEFT]

    def _move_to(self, x, y, w, h, ww, wh, pad=3):
        if Gtk.Widget.get_default_direction() == Gtk.TextDirection.LTR:
            return ((x + w + pad), (y + (h - wh) // 2))
        else:
            return ((x - (ww + pad)), (y + (h - wh) // 2))


class VSlider(_PopupSlider):
    ORIENTATION = Gtk.Orientation.VERTICAL
    _adj = Gtk.Adjustment.new(0, 0, 1, 0.05, 0.1, 0)
    UP = [Gdk.ScrollDirection.UP, Gdk.ScrollDirection.LEFT]
    DOWN = [Gdk.ScrollDirection.DOWN, Gdk.ScrollDirection.RIGHT]

    def _move_to(self, x, y, w, h, ww, wh, pad=3):
        return ((x + (w - ww) // 2), y + h + pad)
