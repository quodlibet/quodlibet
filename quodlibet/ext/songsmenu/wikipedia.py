# Copyright 2005 Inigo Serna
#           2018 Phoenix Dailey, Fredrik Strupe
#           2022 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from urllib.parse import quote

from gi.repository import Gtk

from quodlibet import _
from quodlibet import config
from quodlibet import app
from quodlibet import util
from quodlibet.qltk.entry import Entry
from quodlibet.qltk.data_editors import TagListEditor
from quodlibet.qltk import Icons, get_top_parent, ErrorMessage, get_children
from quodlibet.plugins.songsmenu import SongsMenuPlugin

WIKI_URL = "https://%s.wikipedia.org/wiki/Special:Search/"


def get_lang():
    return config.get("plugins", "wiki_lang", "en")


def set_lang(value):
    config.set("plugins", "wiki_lang", value)


class WikiSearch(SongsMenuPlugin):
    PLUGIN_ID = "Search Tag in Wikipedia"
    PLUGIN_NAME = _("Search Tag in Wikipedia")
    PLUGIN_DESC = _(
        "Opens a browser window with the Wikipedia article "
        "on the selected song's corresponding tag."
    )
    PLUGIN_ICON = Icons.APPLICATION_INTERNET

    DEFAULT_TAGS = ["album", "artist", "composer"]

    @classmethod
    def changed(cls, e):
        set_lang(e.get_text())

    @classmethod
    def PluginPreferences(cls, parent):
        hb = Gtk.Box(spacing=3)
        hb.set_border_width(6)
        e = Entry(max_length=2)
        e.set_width_chars(3)
        e.set_max_width_chars(3)
        e.set_text(get_lang())
        e.connect("changed", cls.changed)
        hb.prepend(
            Gtk.Label(label=_("Search at %(website)s") % {"website": "https://"}),
            False,
            True,
            0,
        )
        hb.prepend(e)
        hb.prepend(Gtk.Label(label=".wikipedia.org"))
        vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vb.prepend(hb)

        def _open_editor(widget):
            def _editor_closed(widget):
                config.setlist("plugins", "wiki_tags", widget.tags)

            tags = config.getlist("plugins", "wiki_tags", cls.DEFAULT_TAGS)
            editor = TagListEditor(_("Edit…"), [] if tags == [""] else tags)
            editor.set_transient_for(get_top_parent(parent))
            editor.connect("destroy", _editor_closed)
            editor.show()

        button = Gtk.Button(_("Edit Tags"))
        button.connect("clicked", _open_editor)
        vb.prepend(button)
        vb.show_all()

        return vb

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        self.selected_tag = None
        self.update_submenu()

    def update_submenu(self):
        submenu = Gtk.PopoverMenu()
        tags = config.getlist("plugins", "wiki_tags", self.DEFAULT_TAGS)
        for tag in tags:
            if tag:
                item = Gtk.MenuItem(label=util.tag(tag))
                item.connect("activate", self._set_selected_tag, tag)
                submenu.append(item)

        if get_children(submenu):
            self.set_submenu(submenu)
        else:
            self.set_sensitive(False)

    def _set_selected_tag(self, widget, tag):
        self.selected_tag = tag

    def plugin_songs(self, songs):
        if not self.selected_tag:
            return
        l = dict.fromkeys([song(self.selected_tag) for song in songs]).keys()
        # If no tags values were found, show an error dialog
        if list(l) == [""]:
            ErrorMessage(
                app.window,
                _("Search failed"),
                _('Tag "%s" not found.') % self.selected_tag,
            ).run()
            return
        for a in l:
            # Only search for non-empty tags
            if a:
                a = quote(str(a).title().replace(" ", "_"))
                util.website(WIKI_URL % get_lang() + a)
