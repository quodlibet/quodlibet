# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, GLib, Gdk, GObject

from quodlibet import config
from quodlibet import qltk
from quodlibet.qltk import bookmarks
from quodlibet.qltk import Icons
from quodlibet import util

from quodlibet.util import connect_obj, connect_destroy, gdecode
from quodlibet.qltk.ccb import ConfigCheckMenuItem
from quodlibet.qltk.sliderbutton import HSlider
from quodlibet.qltk.tracker import TimeTracker
from quodlibet.qltk.x import (RadioMenuItem, SeparatorMenuItem,
                              SymbolicIconImage)


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

    def do_get_preferred_width(self):
        widths = Gtk.Label.do_get_preferred_width(self)

        # If for same number of characters, the needed width was larger,
        # use that instead of the current one
        num_chars = len(gdecode(self.get_text()))
        max_widths = self.__widths.get(num_chars, widths)
        widths = max(widths[0], max_widths[0]), max(widths[1], max_widths[1])
        self.__widths[num_chars] = widths
        return widths

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
            self.set_text(u"‒\u2236‒‒")
        else:
            self.set_time(self._last_time)


class SeekBar(HSlider):
    __lock = False
    __sig = None
    __seekable = True

    def __init__(self, player, library):
        hbox = Gtk.HBox(spacing=3)
        l = TimeLabel()
        self._time_label = l
        hbox.pack_start(l, True, True, 0)
        arrow = Gtk.Arrow.new(Gtk.ArrowType.RIGHT, Gtk.ShadowType.NONE)
        hbox.pack_start(arrow, False, True, 0)
        super(SeekBar, self).__init__(hbox)

        self._slider_label = TimeLabel()
        self.set_slider_widget(self._slider_label)

        self._on_seekable_changed(player)
        connect_destroy(player, "notify::seekable", self._on_seekable_changed)

        self.scale.connect('button-press-event', self.__seek_lock)
        self.scale.connect('button-release-event', self.__seek_unlock, player)
        self.scale.connect('key-press-event', self.__seek_lock)
        self.scale.connect('key-release-event', self.__seek_unlock, player)
        self.connect('scroll-event', self.__scroll, player)
        self.scale.connect('value-changed', self.__update_time, l)

        m = Gtk.Menu()
        c = ConfigCheckMenuItem(
            _("Display remaining time"), "player", "time_remaining")
        c.set_active(config.getboolean("player", "time_remaining"))
        connect_obj(c, 'toggled', self.scale.emit, 'value-changed')
        self.__remaining = c
        m.append(c)
        m.append(SeparatorMenuItem())
        i = qltk.MenuItem(_(u"_Edit Bookmarks…"), Icons.EDIT)

        def edit_bookmarks_cb(menu_item):
            window = bookmarks.EditBookmarks(self, library, player)
            window.show()

        i.connect('activate', edit_bookmarks_cb)
        m.append(i)
        m.show_all()

        connect_obj(self,
            'button-press-event', self.__check_menu, m, player, c)
        connect_obj(self, 'popup-menu', self.__popup_menu, m, player)

        timer = TimeTracker(player)
        connect_obj(timer, 'tick', self.__check_time, player)

        connect_destroy(
            library, "changed", self.__songs_changed, player, m)

        connect_destroy(player, 'song-started', self.__song_started, m)
        connect_destroy(player, 'seek', self.__seeked)

    def _on_seekable_changed(self, player, *args):
        self._time_label.set_disabled(not player.seekable)
        self.set_slider_disabled(not player.seekable)

    def __check_menu(self, menu, event, player, remaining_item):
        if event.type != Gdk.EventType.BUTTON_PRESS:
            return

        if event.button == Gdk.BUTTON_SECONDARY:
            return self.__popup_menu(menu, player, event)
        elif event.button == Gdk.BUTTON_MIDDLE:
            remaining_item.set_active(not remaining_item.get_active())
            return True

    def __popup_menu(self, menu, player, event=None):
        for child in menu.get_children()[2:-1]:
            menu.remove(child)
            child.destroy()

        try:
            marks = player.song.bookmarks
        except AttributeError:
            # song is None
            pass
        else:
            items = qltk.bookmarks.MenuItems(marks, player, self.__seekable)
            items.reverse()
            for i in items:
                menu.insert(i, 2)

        if event:
            qltk.popup_menu_at_widget(menu, self, 3, event.time)
        else:
            time = Gtk.get_current_event_time()
            qltk.popup_menu_under_widget(menu, self, 3, time)
        return True

    def __seeked(self, player, song, ms):
        # If it's not paused, we'll grab it in our next update.
        if player.paused:
            self.scale.set_value(ms // 1000)

    def __scroll(self, widget, event, player):
        self.__lock = True
        if self.__sig is not None:
            GLib.source_remove(self.__sig)
        self.__sig = GLib.timeout_add(100, self.__scroll_timeout, player)

    def __scroll_timeout(self, player):
        self.__lock = False
        if self.__seekable:
            player.seek(self.scale.get_value() * 1000)
        self.__sig = None

    def __seek_lock(self, scale, event):
        self.__lock = True

    def __seek_unlock(self, scale, event, player):
        self.__lock = False
        if self.__seekable:
            player.seek(self.scale.get_value() * 1000)

    def __check_time(self, player):
        # When the song is paused GStreamer returns < 1 for position
        # queries, so if it's paused just ignore it.
        if not (player.paused or self.__lock):
            position = player.get_position() // 1000
            if (not self.__seekable and
                position > self.scale.get_adjustment().get_upper()):
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

    def __songs_changed(self, library, songs, player, menu):
        song = player.song
        if song in songs:
            self.__update_slider(song, menu)

    def __song_started(self, player, song, menu):
        self.scale.set_value(0)
        self.__update_slider(song, menu)

    def __update_slider(self, song, menu):
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

        for child in menu.get_children()[2:-1]:
            menu.remove(child)
            child.destroy()
        menu.get_children()[-1].set_sensitive(self.__seekable)
        self.scale.emit('value-changed')


class Volume(Gtk.VolumeButton):
    def __init__(self, player):
        super(Volume, self).__init__(size=Gtk.IconSize.MENU, use_symbolic=True)

        self.set_relief(Gtk.ReliefStyle.NORMAL)
        self.set_adjustment(Gtk.Adjustment.new(0, 0, 1, 0.05, 0.1, 0))

        popup = self.get_popup()
        if hasattr(Gtk, "Popover") and isinstance(popup, Gtk.Popover):
            popup.set_position(Gtk.PositionType.BOTTOM)

        self._id = self.connect('value-changed', self.__volume_changed, player)
        self._id2 = player.connect('notify::volume', self.__volume_notify)
        self._id3 = player.connect('notify::mute', self.__mute_notify)
        self._orig_icon_list = self.props.icons
        player.notify("volume")
        player.notify("mute")

        self.connect("event", self._on_button_event, player)

        replaygain_menu = VolumeMenu(player)
        self.connect('popup-menu', self.__popup, replaygain_menu)
        connect_obj(self, 'button-press-event', self.__volume_button_press,
                    replaygain_menu, player)

    def __popup(self, widget, menu):
        time = Gtk.get_current_event_time()
        button = 3
        qltk.popup_menu_under_widget(menu, widget, button, time)
        return True

    def __volume_button_press(self, menu, event, player):
        if event.type != Gdk.EventType.BUTTON_PRESS:
            return False

        if event.button == Gdk.BUTTON_SECONDARY:
            qltk.popup_menu_at_widget(menu, self, event.button, event.time)
            return True
        elif event.button == Gdk.BUTTON_MIDDLE:
            # toggle the muted state, if the backend doesn't support it
            # this action will just be ignored
            player.mute = not player.mute
            return True

    def __iadd__(self, v):
        self.set_value(self.get_value() + v)
        return self

    def __isub__(self, v):
        self.set_value(self.get_value() - v)
        return self

    def __volume_changed(self, button, volume, player):
        player.handler_block(self._id2)
        player.volume = volume ** 3.0
        player.handler_unblock(self._id2)

    def __volume_notify(self, player, prop):
        self.handler_block(self._id)
        self.set_value(player.volume ** (1.0 / 3.0))
        self.handler_unblock(self._id)

    def __mute_notify(self, player, prop):
        self._update_mute(player)

    def _update_mute(self, player):
        if player.mute:
            # remove all icons except the mute one to show a muted state
            # that is not affected by the volume slider
            self.props.icons = [self._orig_icon_list[0]]
        else:
            self.props.icons = self._orig_icon_list

    def _on_button_event(self, widget, event, player):
        # pulsesink doesn't emit volume changes when it's paused, but
        # fetching the value works. To prevent user volume changes based on a
        # false starting point update the slider on any action on the
        # volume button.
        self.handler_block(self._id)
        self.set_value(player.volume ** (1.0 / 3.0))
        self.handler_unblock(self._id)
        # same with mute
        self._update_mute(player)


class VolumeMenu(Gtk.Menu):
    __modes = (
        ("auto", _("Auto_matic"), None),
        ("track", _("_Track Mode"), ["track"]),
        ("album", _("_Album Mode"), ["album", "track"])
    )

    def __init__(self, player):
        super(VolumeMenu, self).__init__()

        # ubuntu 12.04..
        if hasattr(player, "bind_property"):
            # Translators: player state, no action
            item = Gtk.CheckMenuItem(label=_("_Mute"), use_underline=True)
            player.bind_property("mute", item, "active",
                                 GObject.BindingFlags.BIDIRECTIONAL)
            self.append(item)
            item.show()

        item = Gtk.MenuItem(label=_("_Replay Gain Mode"), use_underline=True)
        self.append(item)
        item.show()

        rg = Gtk.Menu()
        rg.show()
        item.set_submenu(rg)
        item = None
        for mode, title, profile in self.__modes:
            item = RadioMenuItem(group=item, label=title,
                                 use_underline=True)
            rg.append(item)
            item.connect("toggled", self.__changed, player, profile)
            if player.replaygain_profiles[0] == profile:
                item.set_active(True)
            item.show()

    def __changed(self, item, player, profile):
        if item.get_active():
            player.replaygain_profiles[0] = profile
            player.reset_replaygain()

    def popup(self, *args):
        gain = config.getboolean("player", "replaygain")
        for child in self.get_children():
            child.set_sensitive(gain)
        return super(VolumeMenu, self).popup(*args)


class PlayPauseButton(Gtk.Button):

    __gsignals__ = {
        'toggled': (GObject.SignalFlags.RUN_LAST, None, tuple()),
    }

    def __init__(self):
        super(PlayPauseButton, self).__init__(relief=Gtk.ReliefStyle.NONE)
        self._pause_image = SymbolicIconImage("media-playback-pause",
                                               Gtk.IconSize.LARGE_TOOLBAR)
        self._play_image = SymbolicIconImage("media-playback-start",
                                             Gtk.IconSize.LARGE_TOOLBAR)
        self._set_active(False)
        self.connect("clicked", self._on_clicked)

    def _on_clicked(self, *args):
        self.set_active(not self.get_active())

    def _set_active(self, is_active):
        if self.get_child():
            self.remove(self.get_child())

        if is_active:
            self.add(self._pause_image)
        else:
            self.add(self._play_image)
        self.get_child().show()

        self.emit("toggled")

    def set_active(self, is_active):
        if self.get_active() == is_active:
            return
        self._set_active(is_active)

    def get_active(self):
        return self.get_child() is self._pause_image


class PlayControls(Gtk.VBox):

    def __init__(self, player, library):
        super(PlayControls, self).__init__(spacing=3)

        upper = Gtk.Table(n_rows=1, n_columns=3, homogeneous=True)
        upper.set_row_spacings(3)
        upper.set_col_spacings(3)

        prev = Gtk.Button(relief=Gtk.ReliefStyle.NONE)
        prev.add(SymbolicIconImage("media-skip-backward",
                                   Gtk.IconSize.LARGE_TOOLBAR))
        upper.attach(prev, 0, 1, 0, 1)

        play = PlayPauseButton()
        upper.attach(play, 1, 2, 0, 1)

        next_ = Gtk.Button(relief=Gtk.ReliefStyle.NONE)
        next_.add(SymbolicIconImage("media-skip-forward",
                                    Gtk.IconSize.LARGE_TOOLBAR))
        upper.attach(next_, 2, 3, 0, 1)

        lower = Gtk.Table(n_rows=1, n_columns=3, homogeneous=True)
        lower.set_row_spacings(3)
        lower.set_col_spacings(3)

        self.volume = Volume(player)
        self.volume.set_relief(Gtk.ReliefStyle.NONE)
        lower.attach(self.volume, 0, 1, 0, 1)

        # XXX: Adwaita defines a different padding for GtkVolumeButton
        # We force it to 0 here, which works because the other (normal) buttons
        # in the grid set the width/height
        qltk.add_css(self.volume, """
            .button {
                padding: 0px;
            }
        """)

        seekbar = SeekBar(player, library)
        seekbar.set_relief(Gtk.ReliefStyle.NONE)
        lower.attach(seekbar, 1, 3, 0, 1)

        self.pack_start(upper, False, True, 0)
        self.pack_start(lower, False, True, 0)

        connect_obj(prev, 'clicked', self.__previous, player)
        self._toggle_id = play.connect('toggled', self.__playpause, player)
        play.add_events(Gdk.EventMask.SCROLL_MASK)
        connect_obj(play, 'scroll-event', self.__scroll, player)
        connect_obj(next_, 'clicked', self.__next, player)
        connect_destroy(
            player, 'song-started', self.__song_started, next_, play)
        connect_destroy(
            player, 'paused', self.__on_set_paused_unpaused, play, False)
        connect_destroy(
            player, 'unpaused', self.__on_set_paused_unpaused, play, True)

    def __on_set_paused_unpaused(self, player, button, state):
        # block to prevent a signal cycle in case the paused signal and state
        # get out of sync (shouldn't happen.. but)
        button.handler_block(self._toggle_id)
        button.set_active(state)
        button.handler_unblock(self._toggle_id)

    def __scroll(self, player, event):
        if event.direction in [Gdk.ScrollDirection.UP,
                               Gdk.ScrollDirection.LEFT]:
            player.previous()
        elif event.direction in [Gdk.ScrollDirection.DOWN,
                                 Gdk.ScrollDirection.RIGHT]:
            player.next()

    def __song_started(self, player, song, next, play):
        play.set_active(not player.paused)

    def __playpause(self, button, player):
        if button.get_active() and player.song is None:
            player.reset()
            button.set_active(not player.paused)
        else:
            player.paused = not button.get_active()

    def __previous(self, player):
        player.previous()

    def __next(self, player):
        player.next()
