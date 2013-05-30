# -*- coding: utf-8 -*-
#
# View Lyrics: a Quod Libet plugin for viewing lyrics.
# Copyright (C) 2008, 2011, 2012 Vasiliy Faronov <vfaronov@gmail.com>
#                           2013 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2
# as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You can get a copy of the GNU General Public License at:
# http://www.gnu.org/licenses/gpl-2.0.html


"""Provides the `ViewLyrics` plugin for viewing lyrics in the main window."""

import os

import gtk

from quodlibet import app
from quodlibet.plugins.events import EventPlugin


class ViewLyrics(EventPlugin):
    """The plugin for viewing lyrics in the main window."""

    PLUGIN_ID = 'View Lyrics'
    PLUGIN_NAME = _('View Lyrics')
    PLUGIN_DESC = _('View lyrics beneath the song list.')
    PLUGIN_VERSION = '0.4'

    def enabled(self):
        self.expander = gtk.expander_new_with_mnemonic(_('_Lyrics'))
        self.expander.set_expanded(True)

        self.scrolled_window = gtk.ScrolledWindow()
        self.scrolled_window.set_policy(gtk.POLICY_AUTOMATIC,
                                        gtk.POLICY_AUTOMATIC)
        self.scrolled_window.set_size_request(-1, 200)
        self.adjustment = self.scrolled_window.get_vadjustment()

        self.textview = gtk.TextView()
        self.textbuffer = self.textview.get_buffer()
        self.textview.set_editable(False)
        self.textview.set_cursor_visible(False)
        self.textview.set_wrap_mode(gtk.WRAP_WORD)
        self.textview.set_justification(gtk.JUSTIFY_CENTER)
        self.textview.connect('key-press-event', self.key_press_event_cb)
        self.scrolled_window.add_with_viewport(self.textview)
        self.textview.show()

        self.expander.add(self.scrolled_window)
        self.scrolled_window.show()

        app.window.get_child().pack_start(self.expander, expand=False,
                                      fill=True)

        # We don't show the expander here because it will be shown when a song
        # starts playing (see plugin_on_song_started).

    def disabled(self):
        self.textview.destroy()
        self.scrolled_window.destroy()
        self.expander.destroy()

    def plugin_on_song_started(self, song):
        """Called when a song is started. Loads the lyrics.

        If there are lyrics associated with `song`, load them into the
        lyrics viewer. Otherwise, hides the lyrics viewer.
        """
        if (song is not None) and os.path.exists(song.lyric_filename):
            with open(song.lyric_filename, 'r') as lyric_file:
                self.textbuffer.set_text(lyric_file.read())
            self.adjustment.set_value(0)    # Scroll to the top.
            self.expander.show()
        else:
            self.expander.hide()

    def key_press_event_cb(self, widget, event):
        """Handles up/down "key-press-event" in the lyrics view."""
        adj = self.scrolled_window.get_vadjustment()
        if event.keyval == gtk.keysyms.Up:
            adj.value = max(adj.value - adj.step_increment, adj.lower)
        elif event.keyval == gtk.keysyms.Down:
            adj.value = min(adj.value + adj.step_increment,
                            adj.upper - adj.page_size)
        elif event.keyval == gtk.keysyms.Page_Up:
            adj.value = max(adj.value - adj.page_increment, adj.lower)
        elif event.keyval == gtk.keysyms.Page_Down:
            adj.value = min(adj.value + adj.page_increment,
                            adj.upper - adj.page_size)
        elif event.keyval == gtk.keysyms.Home:
            adj.value = adj.lower
        elif event.keyval == gtk.keysyms.End:
            adj.value = adj.upper - adj.page_size
        else:
            return False
        return True
