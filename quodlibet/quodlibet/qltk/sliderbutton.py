# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk

from quodlibet.qltk import get_top_parent


class _PopupSlider(gtk.EventBox):
    # Based on the Rhythmbox volume control button; thanks to Colin Walters,
    # Richard Hult, Michael Fulbright, Miguel de Icaza, and Federico Mena.

    def __init__(self, child=None, adj=None, req=None):
        super(_PopupSlider, self).__init__()
        button = gtk.Button()
        if child:
            button.add(child)
        self.add(button)
        button.connect('clicked', self.__clicked)
        self.show_all()

        window = self.__window = gtk.Window(gtk.WINDOW_POPUP)
        self.__adj = adj or self._adj

        frame = gtk.Frame()
        frame.set_border_width(0)
        frame.set_shadow_type(gtk.SHADOW_OUT)

        hscale = self.Scale(self.__adj)

        def scale_button_event(widget, event):
            settings = gtk.settings_get_default()
            if not settings:
                return False

            try:
                w = settings.get_property("gtk-primary-button-warps-slider")
            except TypeError:
                return False

            if not w:
                event.button = event.button % 3 + 1

            return False

        hscale.connect("button-press-event", scale_button_event)
        hscale.connect("button-release-event", scale_button_event)

        hscale.set_size_request(*(req or self._req))
        window.connect('button-press-event', self.__button)
        window.connect('key-press-event', self.__key)
        hscale.set_draw_value(False)
        hscale.set_update_policy(gtk.UPDATE_CONTINUOUS)
        self.scale = hscale
        window.add(frame)
        frame.add(hscale)
        self.connect('scroll-event', self.__scroll, hscale)
        self.__window.connect('scroll-event', self.__window_scroll)
        self.scale.connect_object('scroll-event', self.emit, 'scroll-event')

    def __window_scroll(self, window, event):
        self.emit('scroll-event', event)

    def _move_to(self, x, y, w, h, ww, wh, pad=3):
        raise NotImplementedError

    def __clicked(self, button):
        window = self.__window
        frame = window.get_child()
        button = self.get_child()

        if window.get_property('visible'):
            return

        frame.show_all()
        window.size_request()
        x, y = button.get_window().get_origin()
        w, h = button.get_window().get_size()
        ww, wh = window.get_size()
        sx, sy = self._move_to(x, y, w, h, ww, wh, pad=3)
        window.set_transient_for(get_top_parent(self))
        window.move(sx, sy)
        window.show()
        window.grab_focus()
        window.grab_add()

        event_time = gtk.get_current_event_time()

        pointer = gtk.gdk.pointer_grab(
            self.__window.window, True,
            gtk.gdk.BUTTON_PRESS_MASK |
            gtk.gdk.BUTTON_RELEASE_MASK |
            gtk.gdk.BUTTON_MOTION_MASK |
            gtk.gdk.POINTER_MOTION_MASK |
            gtk.gdk.SCROLL_MASK, None, None, event_time)
        keyboard = gtk.gdk.keyboard_grab(window.get_window(), True, event_time)

        if pointer != gtk.gdk.GRAB_SUCCESS or keyboard != gtk.gdk.GRAB_SUCCESS:
            window.grab_remove()
            window.hide()

            if pointer == gtk.gdk.GRAB_SUCCESS:
                gtk.gdk.pointer_ungrab(event_time)
            if keyboard == gtk.gdk.GRAB_SUCCESS:
                gtk.gdk.keyboard_ungrab(event_time)

    def __scroll(self, widget, ev, hscale):
        adj = self.__adj
        v = hscale.get_value()
        if ev.direction in self.UP:
            v += adj.step_increment
        else:
            v -= adj.step_increment
        v = min(adj.upper, max(adj.lower, v))
        hscale.set_value(v)

    def __button(self, widget, ev):
        self.__popup_hide()

    def __key(self, hscale, ev):
        if ev.string in ["\n", "\r", " ", "\x1b"]:  # enter, space, escape
            self.__popup_hide()

    def __popup_hide(self):
        window = self.__window
        event_time = gtk.get_current_event_time()

        window.grab_remove()
        gtk.gdk.pointer_ungrab(event_time)
        gtk.gdk.keyboard_ungrab(event_time)
        window.hide()


class HSlider(_PopupSlider):
    Scale = gtk.HScale
    _req = (200, -1)
    _adj = gtk.Adjustment(0, 0, 0, 3, 15, 0)
    UP = [gtk.gdk.SCROLL_DOWN, gtk.gdk.SCROLL_RIGHT]

    def _move_to(self, x, y, w, h, ww, wh, pad=3):
        if gtk.widget_get_default_direction() == gtk.TEXT_DIR_LTR:
            return ((x + w + pad), (y + (h - wh) // 2))
        else:
            return ((x - (ww + pad)), (y + (h - wh) // 2))


class VSlider(_PopupSlider):
    Scale = gtk.VScale
    _req = (-1, 170)
    _adj = gtk.Adjustment(0, 0, 1, 0.05, 0.1, 0)
    UP = [gtk.gdk.SCROLL_UP, gtk.gdk.SCROLL_LEFT]

    def _move_to(self, x, y, w, h, ww, wh, pad=3):
        return ((x + (w - ww) // 2), y + h + pad)
