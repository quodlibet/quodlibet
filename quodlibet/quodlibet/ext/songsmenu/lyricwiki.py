# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import urllib
from xml.dom import minidom

import gi
gi.require_version("WebKit", "3.0")
from gi.repository import WebKit, Gtk

from quodlibet import app
from quodlibet.util import DeferredSignal, escape
from quodlibet.qltk.window import Window
from quodlibet.plugins.songsmenu import SongsMenuPlugin


class LyricWikiWindow(Window):

    def __init__(self, parent):
        super(LyricWikiWindow, self).__init__(
            default_width=500, default_height=500, dialog=False)
        self.set_transient_for(parent)

        self._defer_set = DeferredSignal(self._set_song, owner=self)

        sw = Gtk.ScrolledWindow()
        self.add(sw)

        self._view = view = WebKit.WebView()

        def scroll_tp_lyrics(view, *args):
            view.execute_script("""
                document.addEventListener('DOMContentLoaded', function() {
                    var box = document.getElementsByClassName('lyricbox')[0];
                    box.scrollIntoView(true);
                }, false);
            """)

        view.connect('load-committed', scroll_tp_lyrics)

        # block messages
        view.connect("console-message", lambda *x: True)

        sw.add(view)
        sw.show_all()

    def enable_tracking(self, player):

        def next_handler(player, song):
            self.set_song(song)

        id_ = player.connect("song-started", next_handler)
        self.connect("destroy", lambda *x: player.disconnect(id_))

    def _set_html(self, message, details=None):
        html = "<center><h2>%s</h2></center>" % escape(message)
        if details:
            html += "<center><p>%s</p><center>" % escape(details)

        self._view.load_html_string(html, "http://foo.bar")

    def set_song(self, song):
        # FIXME: threading

        self._defer_set(song)

    def _set_title(self, message):
        self.set_title(_("Lyrics:") + " " + message)

    def _set_song(self, song):
        if song is None:
            message = _("No active song")
            self._set_html(message)
            self._set_title(message)
            return

        artist, title = song("artist"), song("title")
        artist = urllib.quote(artist.encode('utf-8'))
        title = urllib.quote(title.encode('utf-8'))

        url = ("http://lyrics.wikia.com/api.php?client=QuodLibet&func=getSong"
               "&artist=%s&song=%s&fmt=xml")

        fetch_url = url % (artist, title)
        xml = urllib.urlopen(fetch_url).read()
        dom = minidom.parseString(xml)
        lyrics_node = dom.getElementsByTagName("lyrics")
        url_node = dom.getElementsByTagName("url")

        if not lyrics_node or not url_node or \
                lyrics_node[0].firstChild.data == "Not found":
            message = _("No lyrics found")
            self._set_html(message, song("~artist~title"))
            self._set_title(message)
            return

        page = url_node[0].firstChild.data
        self._view.load_uri(page)
        self._set_title(song("title"))


class LyricWiki(SongsMenuPlugin):
    PLUGIN_ID = 'lyricwiki'
    PLUGIN_NAME = _('Lyrics Window')
    PLUGIN_DESC = _("Shows a window containing lyrics of the playing song")
    PLUGIN_ICON = Gtk.STOCK_FIND

    _window = None

    def _destroy(self, *args):
        type(self)._window = None

    def plugin_songs(self, songs):
        if not songs:
            return
        song = songs[0]

        if not self._window:
            window = LyricWikiWindow(parent=self.plugin_window)
            window.show()
            window.connect("destroy", self._destroy)
            type(self)._window = window
            window.enable_tracking(app.player)
        else:
            window = self._window

        window.set_song(song)
