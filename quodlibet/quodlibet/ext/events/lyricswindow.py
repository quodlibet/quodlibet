# -*- coding: utf-8 -*-
# Copyright 2014 Christoph Reiter
#           2015 Joschua Gandert
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

from quodlibet.plugins import PluginImportException, PluginConfig
import gi
try:
    gi.require_version("WebKit", "3.0")
except ValueError as e:
    raise PluginImportException("GObject Introspection: " + str(e))

from gi.repository import WebKit, Gtk, GLib

from quodlibet import app, qltk
from quodlibet.util import DeferredSignal, escape, cached_property
from quodlibet.qltk.window import Window
from quodlibet.plugins.events import EventPlugin


LYRICS_WIKIA_URL = ("http://lyrics.wikia.com/api.php?client=QuodLibet"
                    "&action=lyrics&func=getSong&artist=%s&song=%s&fmt=xml")


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
        """Stop all active searchs, no callback will be called after this
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

        fetch_url = LYRICS_WIKIA_URL % (artist, title)
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


class LyricsWebViewWindow(Window):

    def __init__(self, conf):
        super(LyricsWebViewWindow, self).__init__(dialog=False)
        self.set_transient_for(app.window)

        self._thread = SearchThread()
        self.connect("destroy", lambda *x: self._thread.stop())

        sw = Gtk.ScrolledWindow()
        self.add(sw)

        self._view = view = WebKit.WebView()
        settings = view.get_settings()
        # for the mobile version
        settings.set_property("user-agent",
            ("Mozilla/5.0 (Linux; Android 5.1.1; Nexus 5 Build/LMY48B; wv) "
             "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0"
             "Chrome/43.0.2357.65 Mobile Safari/537.36"))

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
        
        self.conf = conf
        self.set_zoom_level(conf.zoom_level)
        self.resize(conf.width, conf.height)
        self.move(conf.x, conf.y)
    
    def set_zoom_level(self, zoom_level):
        self._view.set_zoom_level(zoom_level)

    def set_song(self, song):
        """Display lyrics for the given song"""

        if song is None:
            message = _("No active song")
            self._set_html(message)
            self._set_title(message)
            return

        self._thread.search_song(song, self._callback)

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


class ConfProp(object):

    def __init__(self, conf, name, default):
        self._conf = conf
        self._name = name

        self._conf.defaults.set(name, default)

    def __get__(self, *args, **kwargs):
        return self._conf.get(self._name)

    def __set__(self, obj, value):
        self._conf.set(self._name, value)


class IntConfProp(ConfProp):

    def __get__(self, *args, **kwargs):
        return self._conf.getint(self._name)


class FloatConfProp(ConfProp):

    def __get__(self, *args, **kwargs):
        return self._conf.getfloat(self._name)


def get_config(prefix):
    class LyricsWindowConfig(object):

        plugin_conf = PluginConfig(prefix)

        zoom_level = FloatConfProp(plugin_conf, "zoom_level", 1.4)
        width = IntConfProp(plugin_conf, "width", 500)
        height = IntConfProp(plugin_conf, "height", 500)
        x = IntConfProp(plugin_conf, "x", 0)
        y = IntConfProp(plugin_conf, "y", 0)

    return LyricsWindowConfig()


class ConfigLabel(Gtk.Label):
    """Customised Label for configuration, tied to a widget"""

    def __init__(self, text, widget):
        super(Gtk.Label, self).__init__(label=text, use_underline=True)
        self.set_mnemonic_widget(widget)
        self.set_alignment(0.0, 0.5)


class LyricsWindowPrefs(Gtk.VBox):

    def __init__(self, plugin):
        super(LyricsWindowPrefs, self).__init__(spacing=6)

        self.Conf = plugin.Conf
        self.plugin = plugin

        def change_zoom_level(button):
            value = float(button.get_value())
            self.Conf.zoom_level = value
            
            window = self.plugin._window
            if window:
                window.set_zoom_level(value)

        def build_display_widget():
            vb2 = Gtk.VBox(spacing=3)

            hb = Gtk.HBox(spacing=6)
            zoom_level = Gtk.SpinButton(
                adjustment=Gtk.Adjustment.new(
                    self.Conf.zoom_level, -10, 10, 0.1, 1, 0),
                climb_rate=0.1, digits=2)
            zoom_level.set_numeric(True)
            zoom_level.connect('value-changed', change_zoom_level)
            l1 = ConfigLabel(_("_Zoom level:"), zoom_level)
            hb.pack_start(l1, False, True, 0)
            hb.pack_start(zoom_level, False, True, 0)
            vb2.pack_start(hb, False, True, 0)
            return vb2

        frame = qltk.Frame(label=_("Display"), child=build_display_widget())
        frame.set_border_width(6)
        self.pack_start(frame, False, True, 0)



class LyricsWindow(EventPlugin):
    PLUGIN_ID = 'lyricswindow'
    PLUGIN_NAME = _('Lyrics Window')
    PLUGIN_DESC = _("Shows a window containing lyrics of the playing song.")
    PLUGIN_ICON = Gtk.STOCK_FIND

    _window = None

    def _destroy(self, *args):
        self._window = None
    
    def enabled(self):
        if self._window is None:
            self._open_webview_window()
    
    def disabled(self):
        if self._window is not None:
            self._window.close()
        
    @cached_property
    def Conf(self):
        return get_config(self.PLUGIN_ID)
        
    def PluginPreferences(self, parent):
        return LyricsWindowPrefs(self)
        
    def _save_window_size_and_position(self, *args):
        window = self._window
        if window is not None:
            conf = self.Conf
            conf.width, conf.height = window.get_size()
            conf.x, conf.y = window.get_position()
        
    def _open_webview_window(self):
        window = LyricsWebViewWindow(self.Conf)
        window.show()
        window.connect("destroy", self._destroy)
        window.connect("configure-event", self._save_window_size_and_position)
        self._window = window
        return window

    def plugin_on_song_started(self, song):
        window = self._window
        if window is not None:
            window.set_song(song)
