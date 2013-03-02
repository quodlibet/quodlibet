# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, Gdk

from quodlibet.qltk import get_top_parent


class _PopupSlider(Gtk.EventBox):
    # Based on the Rhythmbox volume control button; thanks to Colin Walters,
    # Richard Hult, Michael Fulbright, Miguel de Icaza, and Federico Mena.

    def __init__(self, child=None, adj=None, req=None):
        super(_PopupSlider, self).__init__()
        button = Gtk.Button()
        if child:
            button.add(child)
        self.add(button)
        button.connect('clicked', self.__clicked)
        self.show_all()

        window = self.__window = Gtk.Window(Gtk.WindowType.POPUP)
        self.__adj = adj or self._adj

        frame = Gtk.Frame()
        frame.set_border_width(0)
        frame.set_shadow_type(Gtk.ShadowType.OUT)

        self.add_events(Gdk.EventMask.SCROLL_MASK)

        hscale = self.Scale(adjustment=self.__adj)
        hscale.set_size_request(*(req or self._req))
        window.connect('button-press-event', self.__button)
        window.connect('key-press-event', self.__key)
        hscale.set_draw_value(False)
        self.scale = hscale
        window.add(frame)
        frame.add(hscale)
        self.connect('scroll-event', self.__scroll, hscale)

        def foward_scroll(scale, event):
            self.emit('scroll-event', event.copy())
        self.scale.connect('scroll-event', foward_scroll)

    def _move_to(self, x, y, w, h, ww, wh, pad=3):
        raise NotImplementedError

    def __clicked(self, button):
        if self.__window.get_property('visible'):
            return

        window = self.__window
        button = self.get_child()
        frame = window.get_child()

        frame.show_all()
        window.size_request()

        dummy, x, y = self.get_window().get_origin()
        button_alloc = button.get_allocation()
        w, h = button_alloc.width, button_alloc.height

        ww, wh = window.get_size()
        sx, sy = self._move_to(x, y, w, h, ww, wh, pad=3)
        window.set_transient_for(get_top_parent(self))
        window.move(sx, sy)
        window.show()
        window.grab_focus()
        window.grab_add()

        event_time = Gtk.get_current_event_time()

        pointer = Gdk.pointer_grab(
            window.get_window(), True,
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.BUTTON_MOTION_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.SCROLL_MASK, None, None, event_time)
        keyboard = Gdk.keyboard_grab(window.get_window(), True, event_time)

        grab_sucess = Gdk.GrabStatus.SUCCESS
        if pointer != grab_sucess or keyboard != grab_sucess:
            window.grab_remove()
            window.hide()

            if pointer == Gdk.GrabStatus.SUCCESS:
                Gdk.pointer_ungrab(event_time)
            if keyboard == Gdk.GrabStatus.SUCCESS:
                Gdk.keyboard_ungrab(event_time)

    def __scroll(self, widget, ev, hscale):
        adj = self.__adj
        v = hscale.get_value()
        if ev.direction in self.UP:
            v += adj.props.step_increment
        else:
            v -= adj.props.step_increment
        v = min(adj.props.upper, max(adj.props.lower, v))
        hscale.set_value(v)

    def __button(self, widget, ev):
        self.__popup_hide()

    def __key(self, hscale, ev):
        if ev.string in ["\n", "\r", " ", "\x1b"]:  # enter, space, escape
            self.__popup_hide()

    def __popup_hide(self):
        window = self.__window
        event_time = Gtk.get_current_event_time()

        window.grab_remove()
        Gdk.pointer_ungrab(event_time)
        Gdk.keyboard_ungrab(event_time)
        window.hide()


class HSlider(_PopupSlider):
    Scale = Gtk.HScale
    _req = (200, -1)
    _adj = Gtk.Adjustment(0, 0, 0, 3, 15, 0)
    UP = [Gdk.ScrollDirection.DOWN, Gdk.ScrollDirection.RIGHT]

    def _move_to(self, x, y, w, h, ww, wh, pad=3):
        if Gtk.Widget.get_default_direction() == Gtk.TextDirection.LTR:
            return ((x + w + pad), (y + (h - wh) // 2))
        else:
            return ((x - (ww + pad)), (y + (h - wh) // 2))


class VSlider(_PopupSlider):
    Scale = Gtk.VScale
    _req = (-1, 170)
    _adj = Gtk.Adjustment(0, 0, 1, 0.05, 0.1, 0)
    UP = [Gdk.ScrollDirection.UP, Gdk.ScrollDirection.LEFT]

    def _move_to(self, x, y, w, h, ww, wh, pad=3):
        return ((x + (w - ww) // 2), y + h + pad)
