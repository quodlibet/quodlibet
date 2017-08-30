# -*- coding: utf-8 -*-
# Copyright 2011-2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import quodlibet
from quodlibet import _
from quodlibet import qltk
from quodlibet.formats import AudioFile
from quodlibet.pattern import Pattern
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.qltk.cbes import StandaloneEditor
from quodlibet.qltk.x import SeparatorMenuItem
from quodlibet.qltk import Icons
from quodlibet.util import website
from quodlibet.util.tags import USER_TAGS, MACHINE_TAGS
from quodlibet.util import connect_obj, print_w, print_d
from quodlibet.util.path import uri_is_valid
from quodlibet.compat import quote_plus, text_type

from gi.repository import Gtk
import os


class WebsiteSearch(SongsMenuPlugin):
    """Loads a browser with a URL designed to search on tags of the song.
    This may include a standard web search engine, eg Google, or a more
    specific site look-up. The URLs are customisable using tag patterns.
    """

    PLUGIN_ICON = Icons.APPLICATION_INTERNET
    PLUGIN_ID = "Website Search"
    PLUGIN_NAME = _("Website Search")
    PLUGIN_DESC = _("Searches your choice of website using any song tags.\n"
                    "Supports patterns e.g. %(pattern-example)s.") % {
                        "pattern-example":
                            "https://google.com?q=&lt;~artist~title&gt;"}

    # Here are some starters...
    DEFAULT_URL_PATS = [
        ("Google song search",
            "https://google.com/search?q=<artist~title>"),
        ("Wikipedia (en) artist entry",
            "https://wikipedia.org/wiki/<albumartist|<albumartist>|<artist>>"),
        ("Musicbrainz album listing",
            "https://musicbrainz.org/<musicbrainz_albumid|release/"
            "<musicbrainz_albumid>|search?query=<album>&type=release>"),
        ("Discogs album search",
            "https://www.discogs.com/search?type=release&artist="
            "<albumartist|<albumartist>|<artist>>&title=<album>"),
        ("Youtube video search",
         "https://www.youtube.com/results?search_query=<artist~title>"),
        ("Go to ~website", "<website>"),
    ]
    PATTERNS_FILE = os.path.join(
        quodlibet.get_user_dir(), 'lists', 'searchsites')

    def __set_site(self, name):
        self.chosen_site = name

    def get_url_pattern(self, key):
        """Gets the pattern for a given key"""
        return dict(self._url_pats).get(key, self.DEFAULT_URL_PATS[0][1])

    @classmethod
    def edit_patterns(cls, button):
        def valid_uri(s):
            # TODO: some pattern validation too (that isn't slow)
            try:
                p = Pattern(s)
                return (p and uri_is_valid(s))
            except ValueError:
                return False

        win = StandaloneEditor(filename=cls.PATTERNS_FILE,
                               title=_("Search URL patterns"),
                               initial=cls.DEFAULT_URL_PATS,
                               validator=valid_uri)
        win.show()

    @classmethod
    def PluginPreferences(cls, parent):
        hb = Gtk.HBox(spacing=3)
        hb.set_border_width(0)

        button = qltk.Button(_("Edit search URLs"), Icons.EDIT)
        button.connect("clicked", cls.edit_patterns)
        hb.pack_start(button, True, True, 0)
        hb.show_all()
        return hb

    def _get_saved_searches(self):
        filename = self.PATTERNS_FILE + ".saved"
        self._url_pats = StandaloneEditor.load_values(filename)
        # Failing all else...
        if not len(self._url_pats):
            print_d("No saved searches found in %s. Using defaults." %
                    filename)
            self._url_pats = self.DEFAULT_URL_PATS

    def __init__(self, *args, **kwargs):
        super(WebsiteSearch, self).__init__(*args, **kwargs)
        self.chosen_site = None
        self._url_pats = []
        submenu = Gtk.Menu()
        self._get_saved_searches()
        for name, url_pat in self._url_pats:
            item = Gtk.MenuItem(label=name)
            connect_obj(item, 'activate', self.__set_site, name)
            submenu.append(item)
        # Add link to editor
        configure = Gtk.MenuItem(label=_(u"Configure Searches…"))
        connect_obj(configure, 'activate', self.edit_patterns, configure)
        submenu.append(SeparatorMenuItem())
        submenu.append(configure)
        if submenu.get_children():
            self.set_submenu(submenu)
        else:
            self.set_sensitive(False)

    def plugin_songs(self, songs):
        # Check this is a launch, not a configure
        if self.chosen_site:
            url_pat = self.get_url_pattern(self.chosen_site)
            pat = Pattern(url_pat)
            urls = set()
            for song in songs:
                # Generate a sanitised AudioFile; allow through most tags
                subs = AudioFile()
                for k in (USER_TAGS + MACHINE_TAGS):
                    vals = song.comma(k)
                    if vals:
                        try:
                            encoded = text_type(vals).encode('utf-8')
                            subs[k] = (encoded if k == 'website'
                                       else quote_plus(encoded))
                        # Dodgy unicode problems
                        except KeyError:
                            print_d("Problem with %s tag values: %r"
                                    % (k, vals))
                url = str(pat.format(subs))
                if not url:
                    print_w("Couldn't build URL using \"%s\"."
                            "Check your pattern?" % url_pat)
                    return
                # Grr, set.add() should return boolean...
                if url not in urls:
                    urls.add(url)
                    website(url)
