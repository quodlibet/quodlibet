# Copyright 2011,2013 Christoph Reiter
#                2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk, Gst

if not Gst.ElementFactory.find("chromaprint"):
    from quodlibet import plugins
    raise plugins.MissingGstreamerElementPluginError("chromaprint")

from .submit import FingerprintDialog
from .util import get_api_key

from quodlibet import _
from quodlibet import config
from quodlibet import util
from quodlibet.qltk import Button, Frame, Icons
from quodlibet.qltk.entry import UndoEntry
from quodlibet.qltk.msg import ErrorMessage
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.plugins.songshelpers import is_writable, is_finite, each_song


class AcoustidSearch(SongsMenuPlugin):
    PLUGIN_ID = "AcoustidSearch"
    PLUGIN_NAME = _("Acoustic Fingerprint Lookup")
    PLUGIN_DESC = _("Looks up song metadata through acoustic fingerprinting.")
    PLUGIN_ICON = Icons.NETWORK_WORKGROUP

    plugin_handles = each_song(is_finite, is_writable)

    def plugin_songs(self, songs):
        from .search import SearchWindow

        window = SearchWindow(songs, title=self.PLUGIN_NAME)
        window.show()

        # plugin_done checks for metadata changes and opens the write dialog
        window.connect("destroy", self.__plugin_done)

    def __plugin_done(self, *args):
        self.plugin_finish()


class AcoustidSubmit(SongsMenuPlugin):
    PLUGIN_ID = "AcoustidSubmit"
    PLUGIN_NAME = _("Submit Acoustic Fingerprints")
    PLUGIN_DESC = _("Generates acoustic fingerprints using chromaprint "
                    "and submits them to acoustid.org.")
    PLUGIN_ICON = Icons.NETWORK_WORKGROUP

    plugin_handles = each_song(is_finite, is_writable)

    def plugin_songs(self, songs):
        if not get_api_key():
            ErrorMessage(self, _("API Key Missing"),
                _("You have to specify an acoustid.org API key in the plugin "
                "preferences before you can submit fingerprints.")).run()
        else:
            FingerprintDialog(songs)

    @classmethod
    def PluginPreferences(cls, win):
        box = Gtk.VBox(spacing=12)

        # api key section
        def key_changed(entry, *args):
            config.set("plugins", "fingerprint_acoustid_api_key",
                entry.get_text())

        button = Button(_("Request API key"), Icons.NETWORK_WORKGROUP)
        button.connect("clicked",
            lambda s: util.website("https://acoustid.org/api-key"))
        key_box = Gtk.HBox(spacing=6)
        entry = UndoEntry()
        entry.set_text(get_api_key())
        entry.connect("changed", key_changed)
        label = Gtk.Label(label=_("API _key:"))
        label.set_use_underline(True)
        label.set_mnemonic_widget(entry)
        key_box.pack_start(label, False, True, 0)
        key_box.pack_start(entry, True, True, 0)
        key_box.pack_start(button, False, True, 0)

        box.pack_start(Frame(_("AcoustID Web Service"),
                       child=key_box), True, True, 0)

        return box
