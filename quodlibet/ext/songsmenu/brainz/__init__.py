# Copyright 2005-2010   Joshua Kwan <joshk@triplehelix.org>,
#                       Michael Ball <michael.ball@gmail.com>,
#                       Steven Robertson <steven@strobe.cc>
#                2016   Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from quodlibet import _
from quodlibet.qltk import Icons
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.plugins.songshelpers import is_writable, each_song, is_finite

from .util import pconfig
from .widgets import SearchWindow


class MyBrainz(SongsMenuPlugin):
    PLUGIN_ID = "MusicBrainz lookup"
    PLUGIN_NAME = _("MusicBrainz Lookup")
    PLUGIN_ICON = Icons.MEDIA_OPTICAL
    PLUGIN_DESC = _("Re-tags an album based on a MusicBrainz search.")

    plugin_handles = each_song(is_writable, is_finite)

    def plugin_albums(self, albums):
        if not albums:
            return

        def win_finished_cb(widget, *args):
            if albums:
                start_processing(albums.pop(0))
            else:
                self.plugin_finish()

        def start_processing(disc):
            win = SearchWindow(self.plugin_window, disc)
            win.connect("destroy", win_finished_cb)
            win.show()

        start_processing(albums.pop(0))

    @classmethod
    def PluginPreferences(cls, win):
        items = [
            ("year_only", _('Only use year for "date" tag')),
            ("albumartist", _('Write "_albumartist" when needed')),
            ("artist_sort", _("Write sort tags for artist names")),
            ("standard", _("Write _standard MusicBrainz tags")),
            ("labelid2", _('Write "labelid" tag')),
        ]

        vb = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
        )
        vb.set_spacing(8)

        for key, label in items:
            ccb = pconfig.ConfigCheckButton(label, key, populate=True)
            vb.prepend(ccb)

        return vb
