# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk, GObject

from quodlibet import config
from quodlibet import qltk
from quodlibet.util import connect_obj, connect_destroy
from quodlibet.qltk.x import SymbolicIconImage
from quodlibet.qltk.util import GSignals
from quodlibet.qltk.seekbutton import SeekButton


class Volume(Gtk.VolumeButton):
    def __init__(self, player):
        super().__init__(use_symbolic=True)

        # https://bugzilla.gnome.org/show_bug.cgi?id=781605
        scales = qltk.find_widgets(self.get_popup(), Gtk.Scale)
        if scales:
            scales[0].props.round_digits = -1

        self.set_adjustment(Gtk.Adjustment.new(0, 0, 1, 0.05, 0.1, 0))

        # GTK4: Popover always available
        popup = self.get_popup()
        if isinstance(popup, Gtk.Popover):
            popup.set_position(Gtk.PositionType.BOTTOM)

        self._id = self.connect("value-changed", self.__volume_changed, player)
        self._id2 = player.connect("notify::volume", self.__volume_notify)
        self._id3 = player.connect("notify::mute", self.__mute_notify)
        self._orig_icon_list = self.props.icons
        player.notify("volume")
        player.notify("mute")

    def __iadd__(self, v):
        self.set_value(self.get_value() + v)
        return self

    def __isub__(self, v):
        self.set_value(self.get_value() - v)
        return self

    def __volume_changed(self, button, volume, player):
        player.handler_block(self._id2)
        player.volume = volume
        player.handler_unblock(self._id2)

    def __volume_notify(self, player, prop):
        self.handler_block(self._id)
        self.set_value(player.volume)
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


class PlayPauseButton(Gtk.Button):
    __gsignals__: GSignals = {
        "toggled": (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self):
        super().__init__()
        self._pause_image = SymbolicIconImage(
            "media-playback-pause", Gtk.IconSize.NORMAL
        )
        self._play_image = SymbolicIconImage(
            "media-playback-start", Gtk.IconSize.NORMAL
        )
        self._set_active(False)
        self.connect("clicked", self._on_clicked)

    def _on_clicked(self, *args):
        self.set_active(not self.get_active())

    def _set_active(self, is_active):
        if is_active:
            self.set_child(self._pause_image)
        else:
            self.set_child(self._play_image)
        self.get_child().show()

        self.emit("toggled")

    def set_active(self, is_active):
        if self.get_active() == is_active:
            return
        config.set("player", "is_playing", is_active)
        self._set_active(is_active)

    def get_active(self):
        return self.get_child() is self._pause_image


class PlayControls(Gtk.Box):
    def __init__(self, player, library):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=3)

        upper = Gtk.Grid()
        upper.set_row_spacing(3)
        upper.set_column_spacing(3)
        upper.set_column_homogeneous(True)

        prev = Gtk.Button()
        prev.set_child(SymbolicIconImage("media-skip-backward", Gtk.IconSize.NORMAL))
        prev.set_hexpand(True)
        upper.attach(prev, 0, 0, 1, 1)

        play = PlayPauseButton()
        play.set_hexpand(True)
        upper.attach(play, 1, 0, 1, 1)

        next_ = Gtk.Button()
        next_.set_child(SymbolicIconImage("media-skip-forward", Gtk.IconSize.NORMAL))
        next_.set_hexpand(True)
        upper.attach(next_, 2, 0, 1, 1)

        lower = Gtk.Grid()
        lower.set_row_spacing(3)
        lower.set_column_spacing(3)
        lower.set_column_homogeneous(True)

        self.volume = Volume(player)
        self.volume.set_hexpand(True)
        lower.attach(self.volume, 0, 0, 1, 1)

        # XXX: Adwaita defines a different padding for GtkVolumeButton
        # We force it to 0 here, which works because the other (normal) buttons
        # in the grid set the width/height
        qltk.add_css(
            self.volume,
            """
            .button {
                padding: 0px;
            }
        """,
        )

        seekbutton = SeekButton(player, library)
        seekbutton.set_hexpand(True)
        lower.attach(seekbutton, 1, 0, 2, 1)

        self.append(upper)
        self.append(lower)

        connect_obj(prev, "clicked", self.__previous, player)
        self._toggle_id = play.connect("toggled", self.__playpause, player)
        # GTK4: Use EventControllerScroll instead of scroll-event signal
        scroll_controller = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.VERTICAL
            | Gtk.EventControllerScrollFlags.HORIZONTAL
        )
        scroll_controller.connect("scroll", self.__scroll, player)
        play.add_controller(scroll_controller)
        connect_obj(next_, "clicked", self.__next, player)
        connect_destroy(player, "song-started", self.__song_started, next_, play)
        connect_destroy(player, "paused", self.__on_set_paused_unpaused, play, False)
        connect_destroy(player, "unpaused", self.__on_set_paused_unpaused, play, True)

    def __on_set_paused_unpaused(self, player, button, state):
        # block to prevent a signal cycle in case the paused signal and state
        # get out of sync (shouldn't happen.. but)
        button.handler_block(self._toggle_id)
        button.set_active(state)
        button.handler_unblock(self._toggle_id)

    def __scroll(self, controller, dx, dy, player):
        # GTK4: EventControllerScroll provides dx, dy deltas
        if dy < 0 or dx < 0:
            player.previous()
        elif dy > 0 or dx > 0:
            player.next()
        return True

    def __song_started(self, player, song, next, play):
        play.set_active(not player.paused)

    def __playpause(self, button, player):
        if button.get_active():
            player.play()
        else:
            player.paused = True

    def __previous(self, player):
        player.previous()

    def __next(self, player):
        player.next()
