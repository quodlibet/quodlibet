# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk, Gdk, GObject

from quodlibet import config
from quodlibet import qltk
from quodlibet import _
from quodlibet.util import connect_obj, connect_destroy
from quodlibet.qltk.x import SymbolicIconImage, RadioMenuItem
from quodlibet.qltk.util import GSignals
from quodlibet.qltk.seekbutton import SeekButton
from quodlibet.util.dprint import print_e


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
        # TODO GTK4: Add VolumeMenu with GestureClick controller

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

class VolumeMenu(Gtk.PopoverMenu):
    __modes = (
        ("auto", _("Auto_matic"), None),
        ("track", _("_Track Mode"), ["track"]),
        ("album", _("_Album Mode"), ["album", "track"]),
    )

    def __init__(self, player):
        super().__init__()

        # ubuntu 12.04..
        if hasattr(player, "bind_property"):
            # Translators: player state, no action
            item = Gtk.CheckMenuItem(label=_("_Mute"), use_underline=True)
            player.bind_property(
                "mute", item, "active", GObject.BindingFlags.BIDIRECTIONAL
            )
            self.append(item)
            item.show()

        item = Gtk.MenuItem(label=_("_Replay Gain Mode"), use_underline=True)
        self.append(item)
        item.show()

        # Set replaygain mode as saved in configuration
        replaygain_mode = config.gettext("player", "replaygain_mode", "auto")
        self.__set_mode(player, replaygain_mode)

        rg = Gtk.PopoverMenu()
        item.set_submenu(rg)
        item = None
        for mode, title, _profile in self.__modes:
            item = RadioMenuItem(group=item, label=title, use_underline=True)
            rg.append(item)
            item.connect("toggled", self.__changed, player, mode)
            if replaygain_mode == mode:
                item.set_active(True)
            item.show()

    def __set_mode(self, player, mode):
        selected_mode = next((m for m in self.__modes if m[0] == mode), None)
        if selected_mode is None:
            print_e(f"Invalid selected replaygain mode: {mode!r}")
            selected_mode = self.__modes[0]
            print_e(f"Falling back to replaygain mode: {selected_mode[0]!r}")

        player.replaygain_profiles[0] = selected_mode[2]
        player.reset_replaygain()

    def __changed(self, item, player, mode):
        if item.get_active():
            config.settext("player", "replaygain_mode", mode)
            self.__set_mode(player, mode)

    def popup(self, *args):
        gain = config.getboolean("player", "replaygain")
        for child in qltk.get_children(self):
            child.set_sensitive(gain)
        return super().popup(*args)


class PlayPauseButton(Gtk.Button):
    __gsignals__: GSignals = {
        "toggled": (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self):
        super().__init__()
        self._pause_image = SymbolicIconImage(
            "media-playback-pause", Gtk.IconSize.LARGE_TOOLBAR
        )
        self._play_image = SymbolicIconImage(
            "media-playback-start", Gtk.IconSize.LARGE_TOOLBAR
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
        prev.add(SymbolicIconImage("media-skip-backward", Gtk.IconSize.LARGE_TOOLBAR))
        prev.set_hexpand(True)
        upper.attach(prev, 0, 0, 1, 1)

        play = PlayPauseButton()
        play.set_hexpand(True)
        upper.attach(play, 1, 0, 1, 1)

        next_ = Gtk.Button()
        next_.add(SymbolicIconImage("media-skip-forward", Gtk.IconSize.LARGE_TOOLBAR))
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
        play.add_events(Gdk.EventMask.SCROLL_MASK)
        connect_obj(play, "scroll-event", self.__scroll, player)
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

    def __scroll(self, player, event):
        if event.direction in [Gdk.ScrollDirection.UP, Gdk.ScrollDirection.LEFT]:
            player.previous()
        elif event.direction in [Gdk.ScrollDirection.DOWN, Gdk.ScrollDirection.RIGHT]:
            player.next()

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
