# Copyright 2019 LoveIsGrief
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
from quodlibet import plugins, qltk
from quodlibet.qltk.entry import UndoEntry
from quodlibet.util.thread import call_async_background, Cancellable

try:
    import musicbrainzngs
except ImportError:
    raise plugins.MissingModulePluginException("musicbrainzngs")

from gi.repository import Gtk
from quodlibet import _
from quodlibet.plugins import PluginConfig
from quodlibet.plugins.events import EventPlugin

ATTR_BRAINZ = 'musicbrainz_trackid'
ATTR_RATING = '~#rating'

BRAINZ_APP = "quodlibetMusicBrainzSync"
VERSION = "0.1"

plugin_config = PluginConfig("musicbrainz-sync")
defaults = plugin_config.defaults
defaults.set("username", "")
defaults.set("password", "")


class MusicBrainzSyncPlugin(EventPlugin):
    PLUGIN_ID = "musicbrainzsync"
    VERSION = VERSION
    PLUGIN_NAME = _("MusicBrainz Sync")
    PLUGIN_DESC = _("Syncs the rating of a song with music brainz.")

    def __init__(self):
        super(MusicBrainzSyncPlugin, self).__init__()
        musicbrainzngs.set_rate_limit()
        musicbrainzngs.set_useragent(
            BRAINZ_APP, VERSION, "quodlibet@lists.sacredchao.net"
        )
        musicbrainzngs.auth(
            plugin_config.get("username"),
            plugin_config.get("password")
        )

    def plugin_on_changed(self, songs):
        ratings_dict = {
            song[ATTR_BRAINZ]: int(song[ATTR_RATING] * 100)
            for song in songs
            if ATTR_BRAINZ in song and ATTR_RATING in song
        }
        if len(ratings_dict) > 0:
            call_async_background(
                musicbrainzngs.submit_ratings,
                Cancellable(),
                callback=lambda *args: (),
                kwargs=dict(
                    recording_ratings=ratings_dict,
                ),
            )

    def PluginPreferences(self, parent):
        def changed(entry, key):
            if entry.get_property('sensitive'):
                plugin_config.set(key, entry.get_text())
                musicbrainzngs.auth(
                    plugin_config.get("username"),
                    plugin_config.get("password")
                )

        box = Gtk.VBox(spacing=12)

        # first frame
        table = Gtk.Table(n_rows=5, n_columns=2)
        table.props.expand = False
        table.set_col_spacings(6)
        table.set_row_spacings(6)

        labels = []
        label_names = [_("User_name:"), _("_Password:")]
        for idx, name in enumerate(label_names):
            label = Gtk.Label(label=name)
            label.set_alignment(0.0, 0.5)
            label.set_use_underline(True)
            table.attach(label, 0, 1, idx, idx + 1,
                         xoptions=Gtk.AttachOptions.FILL |
                                  Gtk.AttachOptions.SHRINK)
            labels.append(label)

        row = 0

        # username
        entry = UndoEntry()
        entry.set_text(plugin_config.get('username'))
        entry.connect('changed', changed, 'username')
        table.attach(entry, 1, 2, row, row + 1)
        labels[row].set_mnemonic_widget(entry)
        row += 1

        # password
        entry = UndoEntry()
        entry.set_text(plugin_config.get('password'))
        entry.set_visibility(False)
        entry.connect('changed', changed, 'password')
        table.attach(entry, 1, 2, row, row + 1)
        labels[row].set_mnemonic_widget(entry)
        row += 1

        box.pack_start(qltk.Frame(_("Account"), child=table), True, True, 0)

        return box
