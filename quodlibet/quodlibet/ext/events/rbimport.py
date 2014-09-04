# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import xml.sax
from xml.sax.handler import ContentHandler

from gi.repository import Gtk

from quodlibet import app
from quodlibet import util
from quodlibet.qltk.msg import WarningMessage, ErrorMessage
from quodlibet.util.uri import URI
from quodlibet.util.path import expanduser
from quodlibet.plugins.events import EventPlugin


class RBDBContentHandler(ContentHandler):

    def __init__(self, library):
        ContentHandler.__init__(self)

        self._library = library
        self._current = None
        self._tag = None
        self._changed_songs = []

    def characters(self, content):
        if self._current is not None and self._tag is not None:
            self._current[self._tag] = content

    def startElement(self, name, attrs):
        self._tag = None
        if name == "entry" and attrs.get("type") == "song":
            self._current = {}
        elif name in ("location", "rating", "play-count", "last-played"):
            self._tag = name

    def endElement(self, name):
        self._tag = None
        if name == "entry" and self._current is not None:
            current = self._current
            self._current = None
            if len(current) > 1:
                uri = current.pop("location", "")
                try:
                    p_uri = URI(uri)
                except ValueError:
                    return

                if not p_uri.is_filename:
                    return

                self._process_song(p_uri.filename, current)

    def _process_song(self, path, stats):
        song = self._library.get(path, None)
        if not song:
            return

        mapping = {
            "rating": "~#rating",
            "play-count": "~#playcount",
            "last-played": "~#lastplayed"
        }

        has_changed = False
        for src, dst in mapping.items():
            if src in stats:
                try:
                    value = int(stats[src])
                except ValueError:
                    pass
                else:
                    song[dst] = value
                    has_changed = True

        if has_changed:
            self._changed_songs.append(song)

    def finish(self):
        """Call at the end, also returns amount of imported songs"""

        count = len(self._changed_songs)
        self._library.changed(self._changed_songs)
        self._changed_songs = []
        return count


def do_import(parent, library):
    db_path = expanduser("~/.local/share/rhythmbox/rhythmdb.xml")
    handler = RBDBContentHandler(library)
    try:
        xml.sax.parse(db_path, handler)
    except Exception:
        util.print_exc()
        handler.finish()
        msg = _("Import Failed")
        # FIXME: don't depend on the plugin class here..
        ErrorMessage(parent, RBImport.PLUGIN_NAME, msg).run()
    else:
        count = handler.finish()
        msg = _("Successfully imported ratings and statistics "
                "for %d songs") % count
        # FIXME: this is just a warning so it works with older QL
        WarningMessage(parent, RBImport.PLUGIN_NAME, msg).run()


class RBImport(EventPlugin):
    PLUGIN_ID = "rbimport"
    PLUGIN_NAME = _("Rhythmbox Import")
    PLUGIN_DESC = _("Import ratings and song statistics from Rhythmbox")

    def PluginPreferences(self, *args):
        button = Gtk.Button(label=_("Start Import"))

        def clicked_cb(button):
            do_import(button, app.library)

        button.connect("clicked", clicked_cb)
        return button
