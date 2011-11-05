# -*- coding: utf-8 -*-
# Copyright 2011 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet import config, print_w, print_d, qltk
from quodlibet.const import USERDIR
from quodlibet.formats._audio import AudioFile
from quodlibet.parse._pattern import Pattern
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.qltk.cbes import StandaloneEditor
from quodlibet.util import website
from quodlibet.util.tags import STANDARD_TAGS, MACHINE_TAGS
from urllib2 import quote

import ConfigParser
import gtk
import os
from quodlibet.util.uri import URI


class WebsiteSearch(SongsMenuPlugin):
    """Loads a browser with a URL designed to search on tags of the song. 
    This may include a standard web search engine, eg Google, or a more specific
    site look-up. The URLs are customisable using tag patterns."""
    
    PLUGIN_ICON = gtk.STOCK_OPEN
    PLUGIN_ID = "Website Search"
    PLUGIN_NAME = _("Website Search")
    PLUGIN_DESC = _("Searches your choice of website using any song tags."
                    "Requires QL 2.3.3+")
    PLUGIN_VERSION = '0.2'
    
    # Here are some starters...
    # Sorry, PEP-8 : sometimes you're unrealistic
    DEFAULT_URL_PATS = [
        ("Google song search",
            "http://google.com/search?q=<artist~title>"),
        ("Wikipedia (en) artist entry",
            "http://wikipedia.org/wiki/<albumartist|<albumartist>|<artist>>"),
        ("Musicbrainz album listing",
            "http://musicbrainz.org/<musicbrainz_albumid|release/<musicbrainz_albumid>|search?query=<album>&type=release>"),
        ("ISOHunt FLAC album torrent search",
            "https://isohunt.com/torrents/?ihq=<albumartist|<albumartist>|<artist>>+<album>+flac"),
        ("The Pirate Bay torrent search",
            "http://thepiratebay.org/search/<albumartist|<albumartist>|<artist>> <album>/0/99/100")
    ]
    PATTERNS_FILE = os.path.join(USERDIR, 'lists', 'searchsites')

    @classmethod
    def cfg_get(cls, name, default=None):
        try:
            key = __name__ + "_" + name
            return config.get("plugins", key)
        except (ValueError, ConfigParser.Error):
            print_w("Config entry '%s' not found. Using '%s'" %
                    (key, default,))
            return default

    @classmethod
    def cfg_set(cls, name, value):
        key = __name__ + "_" + name
        config.set("plugins", key, value)

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
                u = URI(s)
                return (p and u.netloc and
                    u.scheme in ["http", "https", "ftp", "file"])
            except ValueError:
                return False

        win = StandaloneEditor(filename=cls.PATTERNS_FILE,
            title=_("Search URL patterns"), initial=cls.DEFAULT_URL_PATS,
            validator=valid_uri)
        win.show()

    @classmethod
    def PluginPreferences(cls, parent):
        hb = gtk.HBox(spacing=3)
        hb.set_border_width(0)

        button = qltk.Button(_("Edit search URLs"), gtk.STOCK_EDIT)
        button.set_tooltip_markup(_("Supports QL patterns\neg "
                "<tt>http://google.com?q=&lt;artist~title&gt;</tt>"))
        button.connect("clicked", cls.edit_patterns)
        hb.pack_start(button, expand=True)
        hb.show_all()
        return hb

    def _get_saved_searches(self):
        filename = self.PATTERNS_FILE + ".saved"
        #print_d("Checking saved searches in %s..." % filename, context=self)
        self._url_pats = StandaloneEditor.load_values(filename)
        # Failing all else...
        if not len(self._url_pats):
            print_d("No saved searches found in %s. Using defaults." %
                    filename, context=self)
            self._url_pats = self.DEFAULT_URL_PATS

    def __init__(self, *args, **kwargs):
        super(WebsiteSearch, self).__init__(*args, **kwargs)
        self.chosen_site = None
        self._url_pats = []
        submenu = gtk.Menu()
        self._get_saved_searches()
        for name,url_pat in self._url_pats:
            item = gtk.MenuItem(name)
            item.connect_object('activate', self.__set_site, name)
            submenu.append(item)
        # Add link to editor
        config = gtk.MenuItem(_("Configure searches..."))
        config.connect_object('activate', self.edit_patterns, config)
        submenu.append(gtk.SeparatorMenuItem())
        submenu.append(config)
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
                for k,v in song.items():
                    if k in (STANDARD_TAGS + MACHINE_TAGS):
                        try: subs[k] = quote(unicode(v).encode('utf-8'))
                        # Dodgy unicode problems
                        except KeyError:
                            print_d("Problem with %s tag value: %r" % (k,v))
                url = str(pat.format(subs))
                if not url:
                    print_w("Couldn't build URL using \"%s\"."
                            "Check your pattern?" % url_pat)
                    return
                # Grr, set.add() should return boolean...
                if url not in urls:
                    urls.add(url)
                    website(url)
