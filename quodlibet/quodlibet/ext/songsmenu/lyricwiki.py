# -*- coding: utf-8 -*-
# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import urllib
import urllib2
import threading
import socket
import Queue
from xml.dom import minidom

from quodlibet.plugins import PluginImportException

import gi
try:
    gi.require_version("WebKit", "3.0")
except ValueError as e:
    raise PluginImportException("GObject Introspection: " + str(e))

from gi.repository import WebKit, Gtk, GLib

from quodlibet import app
from quodlibet.util import DeferredSignal, escape
from quodlibet.qltk.window import Window
from quodlibet.plugins.songsmenu import SongsMenuPlugin


class SearchThread(threading.Thread):
    TIMEOUT = 4.0

    def __init__(self):
        super(SearchThread, self).__init__()
        self.daemon = True
        self._queue = Queue.Queue()
        self._stopped = False
        self._current = None

    def search_song(self, song, done_cb):
        """Trigger a new search, old ones will be canceled"""

        assert song
        assert done_cb

        if not self.is_alive():
            self.start()

        self._current = song
        while not self._queue.empty():
            self._queue.get_nowait()
        self._queue.put((song, done_cb))

    def stop(self):
        """Stop all acitve searchs, no callback will be called after this
           returns.
        """

        self._stopped = True
        self._queue.put((None, None))

    def __idle(self, song, func, *args, **kwargs):
        def delayed():
            if self._stopped or song is not self._current:
                return
            func(song, *args, **kwargs)

        GLib.idle_add(delayed)

    def _do_search(self, song):
        """Returns a URL or None"""

        artist, title = song("artist"), song("title")
        artist = urllib.quote(artist.encode('utf-8'))
        title = urllib.quote(title.encode('utf-8'))

        url = ("http://lyrics.wikia.com/api.php?client=QuodLibet&func=getSong"
               "&artist=%s&song=%s&fmt=xml")

        fetch_url = url % (artist, title)

        try:
            response = urllib2.urlopen(fetch_url, timeout=self.TIMEOUT)
        except (urllib2.URLError, socket.timeout):
            return

        try:
            xml = response.read()
        except IOError:
            return

        try:
            dom = minidom.parseString(xml)
        except Exception:
            # who knows...
            return

        page_id_nodes = dom.getElementsByTagName("page_id")
        if not page_id_nodes or not page_id_nodes[0].hasChildNodes():
            return

        url_nodes = dom.getElementsByTagName("url")
        try:
            page = url_nodes[0].firstChild.data
        except (IndexError, AttributeError):
            return
        else:
            return page

    def run(self):
        while not self._stopped:
            song, cb = self._queue.get()
            if self._stopped:
                break
            result = self._do_search(song)
            self.__idle(song, cb, result)


class LyricWikiWindow(Window):

    def __init__(self, parent):
        super(LyricWikiWindow, self).__init__(
            default_width=500, default_height=500, dialog=False)
        self.set_transient_for(parent)

        self._thread = SearchThread()
        self.connect("destroy", lambda *x: self._thread.stop())

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

    def set_song(self, song):
        """Display lyrics for the given song"""

        if song is None:
            message = _("No active song")
            self._set_html(message)
            self._set_title(message)
            return

        self._thread.search_song(song, self._callback)

    def enable_tracking(self, player):
        """Follow the active playing song"""

        # for tracking wait a bit to not produce lots of http requests
        defer_set = DeferredSignal(self.set_song, owner=self, timeout=50)

        def next_handler(player, song):
            defer_set(song)

        id_ = player.connect("song-started", next_handler)
        self.connect("destroy", lambda *x: player.disconnect(id_))

    def _set_html(self, message, details=None):
        html = "<center><h2>%s</h2></center>" % escape(message)
        if details:
            html += "<center><p>%s</p><center>" % escape(details)

        self._view.load_html_string(html, "http://foo.bar")

    def _callback(self, song, page):
        if page is None:
            message = _("No lyrics found")
            self._set_html(message, song("~artist~title"))
            self._set_title(message)
        else:
            self._view.load_uri(page)
            self._set_title(song("title"))

    def _set_title(self, message):
        self.set_title(_("Lyrics:") + " " + message)


class LyricWiki(SongsMenuPlugin):
    PLUGIN_ID = 'lyricwiki'
    PLUGIN_NAME = _('Lyrics Window')
    PLUGIN_DESC = _("Shows a window containing lyrics of the playing song.")
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
