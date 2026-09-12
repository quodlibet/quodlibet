# Copyright 2005 Joe Wreschnig, Michael Urman
#           2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk, Gdk, GLib

from quodlibet import _
from quodlibet import config
from quodlibet import qltk
from quodlibet import util
from quodlibet.qltk.tracker import TimeTracker
from quodlibet.qltk import bookmarks
from quodlibet.qltk.x import Align
from quodlibet.qltk import Icons
from quodlibet.qltk.ccb import ConfigCheckMenuItem
from quodlibet.util import connect_obj, connect_destroy


class TimeLabel(Gtk.Label):
    """A label for displaying the running time

    It tries to minimize size changes due to unequal character widths
    with the same number of characters.

    e.g. a time display -> 04:20
    """

    def __init__(self, time_=0):
        Gtk.Label.__init__(self)
        self.__widths = {}  # num-chars -> (max-min-width, max-natural-width)
        self._disabled = False
        self.set_time(time_)

    def do_measure(self, orientation, for_size):
        min_, nat, min_base, nat_base = Gtk.Label.do_measure(
            self, orientation, for_size
        )
        if orientation != Gtk.Orientation.HORIZONTAL:
            return min_, nat, min_base, nat_base

        # If for same number of characters, the needed width was larger,
        # use that instead of the current one
        num_chars = len(self.get_text())
        widths = self.__widths.get(num_chars, (min_, nat))
        widths = max(min_, widths[0]), max(nat, widths[1])
        self.__widths[num_chars] = widths
        return widths[0], widths[1], min_base, nat_base

    def set_time(self, time_):
        """Set the time in seconds"""

        self._last_time = time_
        if self._disabled:
            return
        self.set_text(util.format_time_display(time_))

    def set_disabled(self, disabled):
        """Disable the time display temporarily, means there is no meaningful
        time to show. Re-enabling will show the previous time value
        """

        self._disabled = disabled
        if disabled:
            self.set_text("‒∶‒‒")
        else:
            self.set_time(self._last_time)


class HSlider(Gtk.Button):
    """A button that shows a horizontal slider in a popover when clicked.

    Scrolling over the button steps the slider value.
    """

    def __init__(self, child=None):
        super().__init__()
        if child:
            self.set_child(child)

        self._disable_slider = False
        self.__adj = Gtk.Adjustment.new(0, 0, 0, 3, 15, 0)

        hscale = Gtk.Scale(adjustment=self.__adj)
        hscale.set_orientation(Gtk.Orientation.HORIZONTAL)
        hscale.set_draw_value(False)
        self.scale = hscale

        self._box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self._box.append(hscale)

        self._popover = Gtk.Popover()
        self._popover.set_parent(self)
        self._popover.set_position(Gtk.PositionType.TOP)
        self._popover.set_has_arrow(False)
        self._popover.set_child(self._box)

        self.connect("clicked", self.__clicked)

        # forward scroll events on the button to the slider
        scroll = Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.BOTH_AXES)
        scroll.connect("scroll", self.__scroll)
        self.add_controller(scroll)

        self.set_slider_length(200)

    def set_slider_disabled(self, disable):
        """Hide the slider and don't allow showing it again until it is
        enabled again
        """

        self._disable_slider = disable
        if disable:
            self._popover.popdown()

    def set_slider_length(self, length):
        self.scale.set_size_request(length, -1)

    def set_slider_widget(self, widget):
        self._box.append(Align(widget, border=6, left=-3))

    def __clicked(self, button):
        if self._disable_slider:
            return
        self._popover.popup()

    def __scroll(self, controller, dx, dy):
        adj = self.__adj
        v = self.scale.get_value()
        if dy > 0 or dx > 0:
            v -= adj.props.step_increment
        elif dy < 0 or dx < 0:
            v += adj.props.step_increment
        else:
            return False
        v = min(adj.props.upper, max(adj.props.lower, v))
        self.scale.set_value(v)
        return False


class SeekButton(HSlider):
    __lock = False
    __sig = None
    __seekable = True

    def __init__(self, player, library):
        hbox = Gtk.Box(spacing=3)
        l = TimeLabel()
        self._time_label = l
        hbox.append(l)
        arrow = Gtk.Image.new_from_icon_name("pan-end-symbolic")
        hbox.append(arrow)
        super().__init__(hbox)

        self._slider_label = TimeLabel()
        self.set_slider_widget(self._slider_label)

        self._on_seekable_changed(player)
        connect_destroy(player, "notify::seekable", self._on_seekable_changed)

        # user-driven scale changes (dragging, arrow keys) -> debounced seek
        self.scale.connect("change-value", self.__change_value, player)
        self.scale.connect("value-changed", self.__update_time, l)

        # scrolling the button -> debounced seek (the slider value is stepped
        # by HSlider's own scroll controller)
        scroll = Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.BOTH_AXES)
        scroll.connect("scroll", self.__scroll, player)
        self.add_controller(scroll)

        self.__menu = self.__create_menu(library, player)

        click = Gtk.GestureClick()
        click.set_button(0)
        click.connect("pressed", self.__button_pressed, player)
        self.add_controller(click)

        key = Gtk.EventControllerKey()
        key.connect("key-pressed", self.__key_pressed, player)
        self.add_controller(key)

        timer = TimeTracker(player)
        connect_obj(timer, "tick", self.__check_time, player)

        connect_destroy(library, "changed", self.__songs_changed, player)
        connect_destroy(player, "song-started", self.__song_started)
        connect_destroy(player, "seek", self.__seeked)

    def _on_seekable_changed(self, player, *args):
        self._time_label.set_disabled(not player.seekable)
        self.set_slider_disabled(not player.seekable)

    def __create_menu(self, library, player):
        menu = Gtk.Popover()
        menu.set_parent(self)
        menu.set_position(Gtk.PositionType.TOP)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        box.set_margin_start(6)
        box.set_margin_end(6)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        menu.set_child(box)
        self.__menu_box = box
        self.__bookmark_items = []

        remaining = ConfigCheckMenuItem(
            _("Display remaining time"), "player", "time_remaining"
        )
        remaining.set_active(config.getboolean("player", "time_remaining"))
        connect_obj(remaining, "toggled", self.scale.emit, "value-changed")
        self.__remaining = remaining
        box.append(remaining)

        self.__separator = Gtk.Separator()
        box.append(self.__separator)

        edit = qltk.MenuItem(_("_Edit Bookmarks…"), Icons.EDIT)

        def edit_bookmarks_cb(menu_item):
            menu.popdown()
            window = bookmarks.EditBookmarks(self, library, player)
            window.show()

        edit.connect("clicked", edit_bookmarks_cb)
        self.__edit_item = edit
        box.append(edit)

        return menu

    def __refresh_bookmarks(self, player):
        for item in self.__bookmark_items:
            self.__menu_box.remove(item)
        self.__bookmark_items = []

        try:
            marks = player.song.bookmarks
        except AttributeError:
            # song is None
            marks = []

        after = self.__separator
        for item in bookmarks.MenuItems(marks, player, self.__seekable):
            self.__menu_box.insert_child_after(item, after)
            after = item
            self.__bookmark_items.append(item)

        self.__edit_item.set_sensitive(self.__seekable)

    def __button_pressed(self, gesture, n_press, x, y, player):
        button = gesture.get_current_button()
        if button == Gdk.BUTTON_SECONDARY:
            self.__popup_menu(player, x, y)
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)
        elif button == Gdk.BUTTON_MIDDLE:
            self.__remaining.set_active(not self.__remaining.get_active())
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)

    def __key_pressed(self, controller, keyval, keycode, state, player):
        shift = state & Gdk.ModifierType.SHIFT_MASK
        if keyval == Gdk.KEY_Menu or (keyval == Gdk.KEY_F10 and shift):
            self.__popup_menu(player, None, None)
            return True
        return False

    def __popup_menu(self, player, x, y):
        self.__refresh_bookmarks(player)
        if x is not None and y is not None:
            rect = Gdk.Rectangle()
            rect.x = int(x)
            rect.y = int(y)
            rect.width = 1
            rect.height = 1
            self.__menu.set_pointing_to(rect)
        else:
            self.__menu.set_pointing_to(None)
        self.__menu.popup()

    def __seeked(self, player, song, ms):
        self.scale.set_value(ms / 1000.0)

    def __scroll(self, controller, dx, dy, player):
        self.__arm_seek(player)
        return False

    def __change_value(self, scale, scroll_type, value, player):
        self.__arm_seek(player)
        return False

    def __arm_seek(self, player):
        self.__lock = True
        if self.__sig is not None:
            GLib.source_remove(self.__sig)
        self.__sig = GLib.timeout_add(100, self.__seek_timeout, player)

    def __seek_timeout(self, player):
        self.__lock = False
        if self.__seekable:
            player.seek(self.scale.get_value() * 1000)
        self.__sig = None
        return False

    def __check_time(self, player):
        # When the song is paused GStreamer returns < 1 for position
        # queries, so if it's paused just ignore it.
        if not (player.paused or self.__lock):
            position = player.get_position() / 1000.0
            if (
                not self.__seekable
                and position > self.scale.get_adjustment().get_upper()
            ):
                self.scale.set_range(0, position)
            self.scale.set_value(position)
        return True

    def __update_time(self, scale, timer):
        value = scale.get_value()
        max_ = scale.get_adjustment().get_upper()
        remaining = value - max_
        if self.__remaining.get_active():
            remaining, value = value, remaining
        timer.set_time(value)
        self._slider_label.set_time(remaining)

    def __songs_changed(self, library, songs, player):
        song = player.song
        if song in songs:
            self.__update_slider(song)

    def __song_started(self, player, song):
        self.scale.set_value(0)
        self.__update_slider(song)

    def __update_slider(self, song):
        if song and song("~#length") > 0:
            self.scale.set_range(0, song("~#length"))
            slider_width = int(song("~#length") / 1.5) + 80
            self.__seekable = True
        else:
            self.scale.set_range(0, 1)
            slider_width = 0
            self.__seekable = False

        slider_width = min(max(slider_width, 170), 400)
        self.set_slider_length(slider_width)
        self.scale.emit("value-changed")
