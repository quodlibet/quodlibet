# Copyright 2011,2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, Gst

if not Gst.ElementFactory.find("chromaprint"):
    from quodlibet import plugins
    raise plugins.MissingGstreamerElementPluginException("chromaprint")

from .submit import FingerprintDialog
from .util import get_api_key

from quodlibet import config
from quodlibet import util
from quodlibet.qltk import Button, Frame
from quodlibet.qltk.entry import UndoEntry
from quodlibet.qltk.msg import ErrorMessage
from quodlibet.plugins.songsmenu import SongsMenuPlugin


class AcoustidSubmit(SongsMenuPlugin):
    PLUGIN_ID = "AcoustidSubmit"
    PLUGIN_NAME = _("Submit Acoustic Fingerprints")
    PLUGIN_DESC = _("Generates acoustic fingerprints using chromaprint "
        " and submits them to 'acoustid.org'")
    PLUGIN_ICON = Gtk.STOCK_CONNECT
    PLUGIN_VERSION = "0.1"

    def plugin_songs(self, songs):
        if not get_api_key():
            ErrorMessage(self, _("API Key Missing"),
                _("You have to specify an Acoustid.org API key in the plugin "
                "preferences before you can submit fingerprints.")).run()
        else:
            FingerprintDialog(songs)

    @classmethod
    def PluginPreferences(self, win):
        box = Gtk.VBox(spacing=12)

        # api key section
        def key_changed(entry, *args):
            config.set("plugins", "fingerprint_acoustid_api_key",
                entry.get_text())

        button = Button(_("Request API key"), Gtk.STOCK_NETWORK)
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

        box.pack_start(Frame(_("Acoustid Web Service"),
                       child=key_box), True, True, 0)

        return box
