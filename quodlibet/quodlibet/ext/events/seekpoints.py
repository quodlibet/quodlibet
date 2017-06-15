# -*- coding: utf-8 -*-

#This is free and unencumbered software released into the public domain.
#
#Anyone is free to copy, modify, publish, use, compile, sell, or
#distribute this software, either in source code form or as a compiled
#binary, for any purpose, commercial or non-commercial, and by any
#means.
#
#For more information, please refer to <http://unlicense.org>

from gi.repository import GLib, Gtk
from quodlibet import _, app
from quodlibet.qltk.entry import UndoEntry
from quodlibet.plugins import PluginConfigMixin
from quodlibet import qltk
from quodlibet.plugins.songshelpers import has_bookmark
from quodlibet.plugins.events import EventPlugin
from quodlibet.qltk import Icons
from quodlibet.qltk.tracker import TimeTracker

class SeekPointsPlugin(EventPlugin, PluginConfigMixin):
    """The plugin class."""

    PLUGIN_ID = "Seekpoints"
    PLUGIN_NAME = _("Seekpoint bookmarks")
    PLUGIN_ICON = Icons.GO_JUMP
    PLUGIN_CONFIG_SECTION = __name__
    PLUGIN_DESC = _(
       "Store Seekpoints A and/or B for tracks. "
       "Skip to time A and stop after time B when track is played.\n"
       "Note that changing the names of the points below does not "
       "update the actual bookmark names, it only changes which "
       "bookmark names the plugin looks for when deciding whether to seek.")

    CFG_SEEKPOINT_A_TEXT = "A"
    CFG_SEEKPOINT_B_TEXT = "B"
    DEFAULT_A_TEXT = "A"
    DEFAULT_B_TEXT = "B"

    def enabled(self):
        self._SeekPoint_A, self._SeekPoint_B = self._get_SeekPoints()
        self._try_create_tracker(force=True)

    def disabled(self):
        self._try_destroy_tracker()

    def _try_create_tracker(self, force=False):
        """Create the tracker if it does not exist,
           or if forced to, like at plugin enable"""
        if force or not self._tracker_is_enabled:
            self._tracker = TimeTracker(app.player)
            self._tracker.connect('tick', self._on_tick)
            self._tracker_is_enabled = True

    def _try_destroy_tracker(self):
        """Destroy the tracker if it exists"""
        if self._tracker_is_enabled:
            self._tracker.destroy()
            self._tracker_is_enabled = False

    # Seeks to point A if it exists
    def plugin_on_song_started(self, song):
        self._try_create_tracker()
        self._SeekPoint_A, self._SeekPoint_B = self._get_SeekPoints()
        if not self._SeekPoint_A:
            return
        self._seek(self._SeekPoint_A)

    # Finishes track after point B has been reached, if it exists
    def _on_tick(self, tracker):
        if not self._SeekPoint_B:
            self._try_destroy_tracker()
            return

        time = app.player.get_position()//1000
        if self._SeekPoint_B <= time:
            self._seek(app.player.info("~#length"))

    def _get_SeekPoints(self):
        if not app.player.song:
            return None,None

        marks = []
        if has_bookmark(app.player.song):
            marks = app.player.song.bookmarks

        SeekPoint_A = None
        SeekPoint_B = None
        SeekPoint_A_text = self.config_get(self.CFG_SEEKPOINT_A_TEXT,
                                           self.DEFAULT_A_TEXT)
        SeekPoint_B_text = self.config_get(self.CFG_SEEKPOINT_B_TEXT,
                                           self.DEFAULT_B_TEXT)
        for time,mark in marks:
            if mark == SeekPoint_A_text:
                SeekPoint_A = time
            elif mark == SeekPoint_B_text:
                SeekPoint_B = time

        return SeekPoint_A, SeekPoint_B

    def _seek(self, seconds):
        app.player.seek(seconds*1000)

    def PluginPreferences(self, parent):
        vb = Gtk.VBox(spacing=12)

        # Bookmark name to use for point A
        hb = Gtk.HBox(spacing=6)
        entry = UndoEntry()
        entry.set_text(self.config_get(self.CFG_SEEKPOINT_A_TEXT,
                                       self.DEFAULT_A_TEXT))
        entry.connect('changed', self.config_entry_changed,
                      self.CFG_SEEKPOINT_A_TEXT)
        lbl = Gtk.Label(label=_("Bookmark name for point A"))
        entry.set_tooltip_markup(_("Bookmark name to check for when "
            "a track is started, and if found the player seeks to that "
            "timestamp"))
        lbl.set_mnemonic_widget(entry)
        hb.pack_start(lbl, False, True, 0)
        hb.pack_start(entry, True, True, 0)
        vb.pack_start(hb, True, True, 0)


        # Bookmark name to use for point B
        hb = Gtk.HBox(spacing=6)
        entry = UndoEntry()
        entry.set_text(self.config_get(self.CFG_SEEKPOINT_B_TEXT,
                                       self.DEFAULT_B_TEXT))
        entry.connect('changed', self.config_entry_changed,
                      self.CFG_SEEKPOINT_B_TEXT)
        lbl = Gtk.Label(label=_("Bookmark name for point B"))
        entry.set_tooltip_markup(_("Bookmark name to use each tick during "
            "play of a track if it exist. If the current position exceeds "
            "the timestamp, seek to the end of the track."))
        lbl.set_mnemonic_widget(entry)
        hb.pack_start(lbl, False, True, 0)
        hb.pack_start(entry, True, True, 0)
        vb.pack_start(hb, True, True, 0)

        return vb
