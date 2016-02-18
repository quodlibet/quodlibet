# -*- coding: utf-8 -*-
# Copyright 2005-2010   Joshua Kwan <joshk@triplehelix.org>,
#                       Michael Ball <michael.ball@gmail.com>,
#                       Steven Robertson <steven@strobe.cc>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation


from gi.repository import Gtk

from quodlibet.qltk.ccb import ConfigCheckButton
from quodlibet.qltk import Icons
from quodlibet.plugins.songsmenu import SongsMenuPlugin

from .util import config_get
from .widgets import SearchWindow


class MyBrainz(SongsMenuPlugin):
    PLUGIN_ID = "MusicBrainz lookup"
    PLUGIN_NAME = _("MusicBrainz Lookup")
    PLUGIN_ICON = Icons.MEDIA_OPTICAL
    PLUGIN_DESC = _('Re-tags an album based on a MusicBrainz search.')

    cache = {}

    def plugin_albums(self, albums):
        if not albums:
            return

        def win_finished_cb(widget, *args):
            if albums:
                start_processing(albums.pop(0))
            else:
                self.plugin_finish()

        def start_processing(disc):
            win = SearchWindow(
                self.plugin_window, disc, self.cache)
            win.connect("destroy", win_finished_cb)
            win.show()

        start_processing(albums.pop(0))

    @classmethod
    def PluginPreferences(self, win):
        items = [
            ('split_disc', _('Split _disc from album'), True),
            ('split_feat', _('Split _featured performers from track'), False),
            ('year_only', _('Only use year for "date" tag'), False),
            ('albumartist', _('Write "_albumartist" when needed'), True),
            ('artist_sort', _('Write sort tags for artist names'), False),
            ('standard', _('Write _standard MusicBrainz tags'), True),
            ('labelid',
                _('Write _labelid tag (fixes multi-disc albums)'), True),
        ]

        vb = Gtk.VBox()
        vb.set_spacing(8)

        for key, label, default in items:
            ccb = ConfigCheckButton(label, 'plugins', 'brainz_' + key)
            ccb.set_active(config_get(key, default))
            vb.pack_start(ccb, True, True, 0)

        return vb
