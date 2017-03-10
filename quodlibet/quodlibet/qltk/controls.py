# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, Gdk, GObject

from quodlibet import config
from quodlibet import qltk
from quodlibet import _
from quodlibet.util import connect_obj, connect_destroy
from quodlibet.qltk.x import SymbolicIconImage, RadioMenuItem
from quodlibet.qltk.seekbutton import SeekButton
from quodlibet.util.dprint import print_e


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

        # Set replaygain mode as saved in configuration
        replaygain_mode = config.gettext("player", "replaygain_mode", "auto")
        self.__set_mode(player, replaygain_mode)

        rg = Gtk.Menu()
        rg.show()
        item.set_submenu(rg)
        item = None
        for mode, title, profile in self.__modes:
            item = RadioMenuItem(group=item, label=title,
                                 use_underline=True)
            rg.append(item)
            item.connect("toggled", self.__changed, player, mode)
            if replaygain_mode == mode:
                item.set_active(True)
            item.show()

    def __set_mode(self, player, mode):
        selected_mode = next((m for m in self.__modes if m[0] == mode), None)
        if selected_mode is None:
            print_e("Invalid selected replaygain mode: %r" % mode)
            selected_mode = self.__modes[0]
            print_e("Falling back to replaygain mode: %r" % selected_mode[0])

        player.replaygain_profiles[0] = selected_mode[2]
        player.reset_replaygain()

    def __changed(self, item, player, mode):
        if item.get_active():
            config.settext("player", "replaygain_mode", mode)
            self.__set_mode(player, mode)

    def popup(self, *args):
        gain = config.getboolean("player", "replaygain")
        for child in self.get_children():
            child.set_sensitive(gain)
        return super(VolumeMenu, self).popup(*args)


class PlayPauseButton(Gtk.Button):

    def __init__(self, player, relief=Gtk.ReliefStyle.NONE):
        super(PlayPauseButton, self).__init__(relief=relief)

        self.__player = player

        self._pause_image = SymbolicIconImage("media-playback-pause",
                                               Gtk.IconSize.LARGE_TOOLBAR)
        self._play_image = SymbolicIconImage("media-playback-start",
                                             Gtk.IconSize.LARGE_TOOLBAR)
        self._set_active(False)
        self._clicked_id = self.connect('clicked', self._on_clicked)

        self.add_events(Gdk.EventMask.SCROLL_MASK)
        self.connect('scroll-event', self.__scroll, player)

        connect_destroy(
            player, 'song-started', self.__song_started)
        connect_destroy(
            player, 'paused', self.__on_set_paused_unpaused, False)
        connect_destroy(
            player, 'unpaused', self.__on_set_paused_unpaused, True)

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

        self.__playpause(self.__player)

    def set_active(self, is_active):
        if self.get_active() == is_active:
            return
        self._set_active(is_active)

    def get_active(self):
        return self.get_child() is self._pause_image

    def __on_set_paused_unpaused(self, player, state):
        # block to prevent a signal cycle in case the paused signal and state
        # get out of sync (shouldn't happen.. but)
        self.handler_block(self._clicked_id)
        self.set_active(state)
        self.handler_unblock(self._clicked_id)

    def __scroll(self, button, event, player):
        if event.direction in [Gdk.ScrollDirection.UP,
                               Gdk.ScrollDirection.LEFT]:
            player.previous()
        elif event.direction in [Gdk.ScrollDirection.DOWN,
                                 Gdk.ScrollDirection.RIGHT]:
            player.next()

    def __song_started(self, player, song):
        self.set_active(not player.paused)

    def __playpause(self, player):
        if self.get_active() and player.song is None:
            player.reset()
            self.set_active(not player.paused)
        else:
            player.paused = not self.get_active()


class PreviousSongButton(Gtk.Button):

    def __init__(self, player, relief=Gtk.ReliefStyle.NONE):
        super(PreviousSongButton, self).__init__(relief=relief)
        self.add(SymbolicIconImage("media-skip-backward",
                                   Gtk.IconSize.LARGE_TOOLBAR))
        self.connect('clicked', self.__clicked, player)

    def __clicked(self, button, player):
        player.previous()


class NextSongButton(Gtk.Button):

    def __init__(self, player, relief=Gtk.ReliefStyle.NONE):
        super(NextSongButton, self).__init__(relief=relief)
        self.add(SymbolicIconImage("media-skip-forward",
                                   Gtk.IconSize.LARGE_TOOLBAR))
        self.connect('clicked', self.__clicked, player)

    def __clicked(self, button, player):
        player.next()


class PlayControls(Gtk.VBox):

    def __init__(self, player, library):
        super(PlayControls, self).__init__(spacing=3)

        upper = Gtk.Table(n_rows=1, n_columns=3, homogeneous=True)
        upper.set_row_spacings(3)
        upper.set_col_spacings(3)

        prev = PreviousSongButton(player)
        upper.attach(prev, 0, 1, 0, 1)

        play = PlayPauseButton(player)
        upper.attach(play, 1, 2, 0, 1)

        next_ = NextSongButton(player)
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

        seekbutton = SeekButton(player, library)
        seekbutton.set_relief(Gtk.ReliefStyle.NONE)
        lower.attach(seekbutton, 1, 3, 0, 1)

        self.pack_start(upper, False, True, 0)
        self.pack_start(lower, False, True, 0)
