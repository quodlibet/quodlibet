# -*- coding: utf-8 -*-
# Copyright 2011 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from os import path
from quodlibet import config, print_w, print_d
from quodlibet.const import USERDIR
from quodlibet.formats._audio import AudioFile
from quodlibet.parse._pattern import Pattern
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.qltk.cbes import ComboBoxEntrySave
from quodlibet.util import website
from quodlibet.util.tags import STANDARD_TAGS, MACHINE_TAGS
from urllib2 import quote
import ConfigParser
import gtk


class WebsiteSearch(SongsMenuPlugin):
    """Loads a browser with a URL designed to search on tags of the song. 
    This may include a standard web search engine, eg Google, or a more specific
    site search. The URL is customisable using tag patterns."""
    
    PLUGIN_ICON = gtk.STOCK_OPEN
    PLUGIN_NAME = _('Website Search')
    PLUGIN_DESC = _('Searches your choice of website using any song tags')    
    PLUGIN_VERSION = '0.1'
    
    CFG_KEY_URL_PAT = "url_pattern"
    # Here are some starters...
    DEFAULT_URL_PATS = [
        # Google song search
        "http://google.com/search?q=<artist~title>",
        # Musicbrainz album listing
        "http://musicbrainz.org/release/<musicbrainz_albumid>",
        # ISOHunt FLAC album torrent search
        "https://isohunt.com/torrents/?ihq=<albumartist|<albumartist>|<artist>>+<album>+flac",
        # The Pirate bay torrent search
        "http://thepiratebay.org/search/<albumartist|<albumartist>|<artist>> <album>/0/99/100"
    ]

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

    @classmethod
    def get_url_pattern(cls):
        return cls.cfg_get(cls.CFG_KEY_URL_PAT, cls.DEFAULT_URL_PATS[0])

    @classmethod
    def changed_url(self, cbe):
        self.cfg_set(self.CFG_KEY_URL_PAT, cbe.child.get_text())

    @classmethod
    def PluginPreferences(cls, parent):
        hb = gtk.HBox(spacing=3)
        hb.set_border_width(0)

        # Allow saved entries etc
        cbes = ComboBoxEntrySave(filename=path.join(USERDIR, "search_sites"),
                initial=cls.DEFAULT_URL_PATS, title=_("Search URL patterns"))
        cbes.set_tooltip_markup(_("Supports QL patterns\neg "
            "<tt>http://google.com?q=&lt;artist~title&gt;</tt>"))
        cbes.connect('changed', cls.changed_url)
        cbes.child.set_text(cls.get_url_pattern())

        lbl = gtk.Label("_URL:")
        lbl.set_mnemonic_widget(cbes)
        lbl.set_use_underline(True)
        hb.pack_start(lbl, expand=False)
        hb.pack_start(cbes, expand=True)
        hb.show_all()
        return hb

    def plugin_songs(cls, songs):
        url_pat = cls.get_url_pattern()
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
                print_w("Couldn't build URL using \"%s\". Check your pattern?"%
                        url_pat)
                return
            # Grr, set.add() should return boolean...
            if url not in urls:
                urls.add(url)
                website(url)
