#
# View Lyrics: a Quod Libet plugin for viewing lyrics.
# Copyright (C) 2008, 2011, 2012 Vasiliy Faronov <vfaronov@gmail.com>
#                        2013-25 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import re

from gi.repository import Gtk, Gdk

from quodlibet import _, config, print_d, app
from quodlibet import qltk
from quodlibet.plugins.events import EventPlugin
from quodlibet.plugins.gui import UserInterfacePlugin
from quodlibet.qltk import Icons, add_css, Button
from quodlibet.qltk.ccb import ConfigCheckButton
from quodlibet.qltk.properties import SongProperties
from quodlibet.util.songwrapper import SongWrapper


class ViewLyrics(EventPlugin, UserInterfacePlugin):
    """The plugin for viewing lyrics in the main window."""

    PLUGIN_ID = "View Lyrics"
    PLUGIN_NAME = _("View Lyrics")
    PLUGIN_DESC = _("Automatically displays tag or file-based lyrics in a sidebar.")
    PLUGIN_ICON = Icons.FORMAT_JUSTIFY_FILL

    def enabled(self):
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
        )
        self.adjustment = self.scrolled_window.get_vadjustment()

        self.textview = Gtk.TextView()
        self.textbuffer = self.textview.get_buffer()
        self._italics = self.textbuffer.create_tag(
            "italic", style="italic", foreground="grey"
        )
        self.textview.set_editable(False)
        self.textview.set_cursor_visible(False)
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.textview.set_justification(Gtk.Justification.CENTER)
        self.textview.connect("key-press-event", self.key_press_event_cb)
        add_css(self.textview, "* { padding: 6px; }")
        vbox = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
        )
        vbox.prepend(self.textview)
        self._edit_button = Button("Edit Lyrics", Icons.EDIT)
        hbox = Gtk.Box()
        hbox.append(self._edit_button)
        vbox.prepend(hbox)
        self.scrolled_window.set_child(vbox)
        self.textview.show()

        self.scrolled_window.show()
        self._sig = None
        cur = app.player.info
        if cur is not None:
            cur = SongWrapper(cur)
        self.plugin_on_song_started(cur)

    def create_sidebar(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, margin=0)
        vbox.prepend(self.scrolled_window)
        vbox.show_all()
        return vbox

    def disabled(self):
        self.textview = None
        self.scrolled_window.close()
        self.scrolled_window = None

    def _hide_timestamps(self, lyrics: str):
        """Remove timestamps from the lyrics if they are formatted as an .lrc file."""
        new_lines = []
        for line in lyrics.splitlines():
            line = line.strip()

            if not line:
                new_lines.append("")
                continue

            match = re.fullmatch(r"\[(\d\d:\d\d\.\d\d\]\s?(.*)|[^\]]+:[^\]]*\])", line)

            if match is None:
                # at least one line isn't formatted as .lrc - keep original text
                return lyrics

            # lines containing ID tags are ignored
            if match.groups()[1] is not None:
                # remove word timestamps in enhanced format
                sentence = "".join(
                    re.split(r"<\d\d:\d\d\.\d\d>\s*", match.groups()[1])
                ).strip()
                if sentence:
                    new_lines.append(sentence)

        return "\n".join(new_lines)

    def plugin_on_song_started(self, song):
        """Called when a song is started. Loads the lyrics.

        If there are lyrics associated with `song`, load them into the
        lyrics viewer. Otherwise, hides the lyrics viewer.
        """
        lyrics = None
        if song is not None:
            print_d("Looking for lyrics for {}".format(song("~filename")))
            lyrics = song("~lyrics")
            if lyrics:
                if config.getboolean("plugins", "view_lyrics_hide_timestamps", True):
                    lyrics = self._hide_timestamps(lyrics)
                self.textbuffer.set_text(lyrics)
                self.adjustment.set_value(0)  # Scroll to the top.
                self.textview.show()
            else:
                title = _("No lyrics found for\n %s") % song("~basename")
                self._set_italicised(title)

            def edit(widget):
                print_d("Launching lyrics editor for {}".format(song("~filename")))
                assert isinstance(song, SongWrapper)
                edit_properties = SongProperties(app.librarian, [song._song])
                edit_properties.switch_to_lyrics()
                edit_properties.show()

            if self._sig:
                self._edit_button.disconnect(self._sig)
            self._sig = self._edit_button.connect("clicked", edit)

    def _set_italicised(self, title):
        self.textbuffer.set_text(title)
        start = self.textbuffer.get_start_iter()
        end = self.textbuffer.get_end_iter()
        self.textbuffer.remove_all_tags(start, end)
        self.textbuffer.apply_tag(self._italics, start, end)

    def plugin_on_changed(self, songs):
        cur = app.player.info
        if cur:
            fn = cur("~filename")
            for s in songs:
                if s("~filename") == fn:
                    print_d("Active song changed, reloading lyrics")
                    self.plugin_on_song_started(SongWrapper(cur))
        else:
            self._set_italicised(_("No active song"))

    def key_press_event_cb(self, widget, event):
        """Handles up/down "key-press-event" in the lyrics view."""
        adj = self.scrolled_window.get_vadjustment().props
        if event.keyval == Gdk.KEY_Up:
            adj.value = max(adj.value - adj.step_increment, adj.lower)
        elif event.keyval == Gdk.KEY_Down:
            adj.value = min(adj.value + adj.step_increment, adj.upper - adj.page_size)
        elif event.keyval == Gdk.KEY_Page_Up:
            adj.value = max(adj.value - adj.page_increment, adj.lower)
        elif event.keyval == Gdk.KEY_Page_Down:
            adj.value = min(adj.value + adj.page_increment, adj.upper - adj.page_size)
        elif event.keyval == Gdk.KEY_Home:
            adj.value = adj.lower
        elif event.keyval == Gdk.KEY_End:
            adj.value = adj.upper - adj.page_size
        else:
            return False
        return True

    def PluginPreferences(self, parent):
        box = Gtk.Box()
        ccb = ConfigCheckButton(
            _("Hide timestamps of .lrc or .elrc formatted lyrics"),
            "plugins",
            "view_lyrics_hide_timestamps",
        )
        hide_timestamps = config.getboolean(
            "plugins", "view_lyrics_hide_timestamps", True
        )
        ccb.set_active(hide_timestamps)
        box.prepend(qltk.Frame(_("Preferences"), child=ccb), True, True, 0)
        return box
