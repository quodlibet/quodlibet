# Copyright 2005 Joe Wreschnig, Michael Urman
#           2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, Gdk

from quodlibet.qltk import get_top_parent, gtk_version


class PrimaryWarpsRange(Gtk.Range):
    """A GtkRange which behaves as if gtk-primary-button-warps-slider
    was always True.

    Adjusts key events depending on the current settings value.
    """

    def __init__(self, *args, **kwargs):
        super(PrimaryWarpsRange, self).__init__(*args, **kwargs)
        self.connect("button-press-event", self.__button_event)
        self.connect("button-release-event", self.__button_event)

    @property
    def _warps(self):
        settings = Gtk.Settings.get_default()
        if settings:
            return settings.get_property("gtk-primary-button-warps-slider")
        return False

    def __button_event(self, widget, event):
        if not self._warps:
            event.button = event.button % 3 + 1
        return False


class PrimaryWarpsScale(Gtk.Scale, PrimaryWarpsRange):
    pass


class _PopupSlider(Gtk.Button):
    # Based on the Rhythmbox volume control button; thanks to Colin Walters,
    # Richard Hult, Michael Fulbright, Miguel de Icaza, and Federico Mena.

    def __init__(self, child=None, adj=None, req=None):
        super(_PopupSlider, self).__init__()
        if child:
            self.add(child)
        self.connect('clicked', self.__clicked)

        window = self.__window = Gtk.Window(Gtk.WindowType.POPUP)
        self.__adj = adj or self._adj

        frame = Gtk.Frame()
        frame.set_border_width(0)
        frame.set_shadow_type(Gtk.ShadowType.OUT)

        self.add_events(Gdk.EventMask.SCROLL_MASK)

        hscale = PrimaryWarpsScale(adjustment=self.__adj)
        hscale.set_orientation(self.ORIENTATION)
        hscale.set_size_request(*(req or self._req))
        window.connect('button-press-event', self.__button)
        window.connect('key-press-event', self.__key)
        hscale.set_draw_value(False)
        self.scale = hscale
        window.add(frame)
        frame.add(hscale)
        self.connect('scroll-event', self.__scroll, hscale)

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

        if child:
            self.get_child().show_all()

    def _move_to(self, x, y, w, h, ww, wh, pad=3):
        raise NotImplementedError

    def __clicked(self, button):
        if self.__window.get_property('visible'):
            return

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
        window = self.__window
        event_time = Gtk.get_current_event_time()

        window.grab_remove()
        Gdk.pointer_ungrab(event_time)
        Gdk.keyboard_ungrab(event_time)
        window.hide()
        #gtk3.8 bug: https://bugzilla.gnome.org/show_bug.cgi?id=700185
        window.unrealize()


class HSlider(_PopupSlider):
    ORIENTATION = Gtk.Orientation.HORIZONTAL
    _req = (200, -1)
    _adj = Gtk.Adjustment(0, 0, 0, 3, 15, 0)
    UP = [Gdk.ScrollDirection.DOWN, Gdk.ScrollDirection.RIGHT]
    DOWN = [Gdk.ScrollDirection.UP, Gdk.ScrollDirection.LEFT]

    def _move_to(self, x, y, w, h, ww, wh, pad=3):
        if Gtk.Widget.get_default_direction() == Gtk.TextDirection.LTR:
            return ((x + w + pad), (y + (h - wh) // 2))
        else:
            return ((x - (ww + pad)), (y + (h - wh) // 2))


class VSlider(_PopupSlider):
    ORIENTATION = Gtk.Orientation.VERTICAL
    _req = (-1, 170)
    _adj = Gtk.Adjustment(0, 0, 1, 0.05, 0.1, 0)
    UP = [Gdk.ScrollDirection.UP, Gdk.ScrollDirection.LEFT]
    DOWN = [Gdk.ScrollDirection.DOWN, Gdk.ScrollDirection.RIGHT]

    def _move_to(self, x, y, w, h, ww, wh, pad=3):
        return ((x + (w - ww) // 2), y + h + pad)
