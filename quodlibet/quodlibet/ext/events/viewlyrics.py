# -*- coding: utf-8 -*-
#
# View Lyrics: a Quod Libet plugin for viewing lyrics.
# Copyright (C) 2008, 2011, 2012 Vasiliy Faronov <vfaronov@gmail.com>
#                        2013-17 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2
# as published by the Free Software Foundation.

from gi.repository import Gtk, Gdk

from quodlibet import _, print_d, app
from quodlibet.plugins.events import EventPlugin
from quodlibet.plugins.gui import UserInterfacePlugin
from quodlibet.qltk import Icons, add_css


class ViewLyrics(EventPlugin, UserInterfacePlugin):
    """The plugin for viewing lyrics in the main window."""

    PLUGIN_ID = 'View Lyrics'
    PLUGIN_NAME = _('View Lyrics')
    PLUGIN_DESC = _('Automatically displays tag or file-based lyrics '
                    'in a sidebar.')
    PLUGIN_ICON = Icons.FORMAT_JUSTIFY_FILL

    def enabled(self):
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC,
                                        Gtk.PolicyType.AUTOMATIC)
        self.adjustment = self.scrolled_window.get_vadjustment()

        self.textview = Gtk.TextView()
        self.textbuffer = self.textview.get_buffer()
        self._italics = self.textbuffer.create_tag("italic", style="italic",
                                                   foreground="grey")
        self.textview.set_editable(False)
        self.textview.set_cursor_visible(False)
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.textview.set_justification(Gtk.Justification.CENTER)
        self.textview.connect('key-press-event', self.key_press_event_cb)
        add_css(self.textview, "* { padding: 6px; }")
        self.scrolled_window.add(self.textview)
        self.textview.show()

        self.scrolled_window.show()
        self.plugin_on_song_started(app.player.info)

        # We don't show the expander here because it will be shown when a song
        # starts playing (see plugin_on_song_started).

    def create_sidebar(self):
        vbox = Gtk.VBox(margin=0)
        vbox.pack_start(self.scrolled_window, True, True, 0)
        vbox.show_all()
        return vbox

    def disabled(self):
        self.textview.destroy()
        self.scrolled_window.destroy()

    def plugin_on_song_started(self, song):
        """Called when a song is started. Loads the lyrics.

        If there are lyrics associated with `song`, load them into the
        lyrics viewer. Otherwise, hides the lyrics viewer.
        """
        lyrics = None
        if song is not None:
            print_d("Attempting to load lyrics for %s" % song("~filename"))
            lyrics = song("~lyrics")
            if lyrics:
                self.textbuffer.set_text(lyrics)
                self.adjustment.set_value(0)    # Scroll to the top.
                self.textview.show()
            else:
                title = _("No lyrics found for\n %s") % song("~basename")
                self.textbuffer.set_text(title)
                start = self.textbuffer.get_start_iter()
                end = self.textbuffer.get_end_iter()
                self.textbuffer.remove_all_tags(start, end)
                self.textbuffer.apply_tag(self._italics, start, end)

    def key_press_event_cb(self, widget, event):
        """Handles up/down "key-press-event" in the lyrics view."""
        adj = self.scrolled_window.get_vadjustment().props
        if event.keyval == Gdk.KEY_Up:
            adj.value = max(adj.value - adj.step_increment, adj.lower)
        elif event.keyval == Gdk.KEY_Down:
            adj.value = min(adj.value + adj.step_increment,
                            adj.upper - adj.page_size)
        elif event.keyval == Gdk.KEY_Page_Up:
            adj.value = max(adj.value - adj.page_increment, adj.lower)
        elif event.keyval == Gdk.KEY_Page_Down:
            adj.value = min(adj.value + adj.page_increment,
                            adj.upper - adj.page_size)
        elif event.keyval == Gdk.KEY_Home:
            adj.value = adj.lower
        elif event.keyval == Gdk.KEY_End:
            adj.value = adj.upper - adj.page_size
        else:
            return False
        return True
