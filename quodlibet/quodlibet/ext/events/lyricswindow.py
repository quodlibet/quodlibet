# -*- coding: utf-8 -*-
# Copyright 2014 Christoph Reiter
#           2015 Joschua Gandert
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import threading
from xml.dom import minidom

from quodlibet import _
from quodlibet.util import gi_require_versions, is_windows, is_osx
from quodlibet.plugins.events import EventPlugin
from quodlibet.plugins import (PluginImportException, PluginConfig, ConfProp,
    BoolConfProp, IntConfProp, FloatConfProp, PluginNotSupportedError)

try:
    gi_require_versions("WebKit2", ["4.0", "3.0"])
except ValueError as e:
    if is_windows() or is_osx():
        raise PluginNotSupportedError
    raise PluginImportException("GObject Introspection: " + str(e))

from gi.repository import WebKit2, Gtk, GLib

from quodlibet import app, qltk
from quodlibet.util import escape, cached_property, connect_obj
from quodlibet.qltk import Icons
from quodlibet.qltk.window import Window
from quodlibet.qltk.entry import UndoEntry
from quodlibet.pattern import URLFromPattern
from quodlibet.compat import quote, queue
from quodlibet.util.urllib import urlopen


# for the mobile version
USER_AGENT = ("Mozilla/5.0 (Linux; Android 5.1.1; Nexus 5 Build/LMY48B; wv) "
             "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0"
             "Chrome/43.0.2357.65 Mobile Safari/537.36")
LYRICS_WIKIA_URL = ("https://lyrics.wikia.com/api.php?client=QuodLibet"
                    "&action=lyrics&func=getSong&artist=%s&song=%s&fmt=xml")
DEFAULT_ALTERNATE_SEARCH_URL = ("https://duckduckgo.com/"
                                "?q=lyrics+<artist|<artist>+-+><title>")


def create_api_search_url(song):
    artist, title = song("artist"), song("title")
    artist = quote(artist.encode('utf-8'))
    title = quote(title.encode('utf-8'))

    return LYRICS_WIKIA_URL % (artist, title)


class LyricsWikiaSearchThread(threading.Thread):
    TIMEOUT = 4.0

    def __init__(self):
        super(LyricsWikiaSearchThread, self).__init__()
        self.daemon = True
        self._queue = queue.Queue()
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
        """Stop all active searches, no callback will be called after this
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

        fetch_url = create_api_search_url(song)
        try:
            response = urlopen(fetch_url, timeout=self.TIMEOUT)
        except EnvironmentError:
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

        self.conf = conf
        self.resize(conf.width, conf.height)
        self.move(conf.x, conf.y)

        self._thread = LyricsWikiaSearchThread()
        self.connect("destroy", lambda *x: self._thread.stop())

        self._scrolled_window = Gtk.ScrolledWindow()
        self.add(self._scrolled_window)

        self.current_song = None
        self._reload_web_view()

    def _reload_web_view(self, web_view=None):
        if web_view is not None:
            self._scrolled_window.remove(web_view)

        self._view = view = WebKit2.WebView()
        self.set_zoom_level(self.conf.zoom_level)

        # stop alert windows
        view.connect('script-dialog', lambda *args: True)

        view.connect('web-process-crashed', self._reload_web_view)

        settings = view.get_settings()
        settings.set_property("user-agent", USER_AGENT)
        settings.set_media_playback_requires_user_gesture(True)

        def scroll_tp_lyrics(view, load_event):
            if load_event != WebKit2.LoadEvent.COMMITTED:
                return

            view.run_javascript("""
                document.addEventListener('DOMContentLoaded', function() {
                    var box = document.getElementsByClassName('lyricbox')[0];
                    box.scrollIntoView(true);
                }, false);
            """, None, None, None)

        view.connect('load-changed', scroll_tp_lyrics)

        self._scrolled_window.add(view)
        self._scrolled_window.show_all()

        if self.current_song is not None:
            self.set_song(self.current_song)

    def set_zoom_level(self, zoom_level):
        self._view.set_zoom_level(zoom_level)

    def set_song(self, song):
        """Display lyrics for the given song"""
        self.current_song = song

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

        self._view.load_html(html, "http://foo.bar")

    def _callback(self, song, page):
        if page is None:
            message = _("No lyrics found")
            if self.conf.alternate_search_enabled:
                url = URLFromPattern(self.conf.alternate_search_url) % song
                self._view.load_uri(url)
            else:
                self._set_html(message, song("~artist~title"))
            self._set_title(message)
        else:
            self._view.load_uri(page)
            self._set_title(song("title"))

    def _set_title(self, message):
        self.set_title(_("Lyrics:") + " " + message)


def get_config(prefix):
    class LyricsWindowConfig(object):

        plugin_conf = PluginConfig(prefix)

        alternate_search_url = ConfProp(plugin_conf, "alternate_search_url",
            DEFAULT_ALTERNATE_SEARCH_URL)
        alternate_search_enabled = BoolConfProp(plugin_conf,
            "alternate_search_enabled", True)
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

        def build_display_widget():
            vb2 = Gtk.VBox(spacing=3)

            hb = Gtk.HBox(spacing=6)
            zoom_level = Gtk.SpinButton(
                adjustment=Gtk.Adjustment.new(
                    self.Conf.zoom_level, -10, 10, 0.1, 1, 0),
                climb_rate=0.1, digits=2)
            zoom_level.set_numeric(True)

            def change_zoom_level(button):
                value = float(button.get_value())
                self.Conf.zoom_level = value

                window = self.plugin._window
                if window:
                    window.set_zoom_level(value)

            zoom_level.connect('value-changed', change_zoom_level)
            l1 = ConfigLabel(_("_Zoom level:"), zoom_level)
            hb.pack_start(l1, False, True, 0)
            hb.pack_start(zoom_level, False, True, 0)
            vb2.pack_start(hb, False, True, 0)
            return vb2

        def build_alternate_search_widget():
            vb2 = Gtk.VBox(spacing=3)

            hb = Gtk.HBox(spacing=6)

            def on_entry_changed(entry, *args):
                self.Conf.alternate_search_url = entry.get_text()

            URL_entry = UndoEntry()
            URL_entry.set_text(self.Conf.alternate_search_url)
            URL_entry.connect("changed", on_entry_changed)

            l1 = ConfigLabel(_("URL:"), URL_entry)

            URL_revert = Gtk.Button()
            URL_revert.add(Gtk.Image.new_from_icon_name(
                Icons.DOCUMENT_REVERT, Gtk.IconSize.MENU))
            URL_revert.set_tooltip_text(_("Revert to default"))

            connect_obj(URL_revert, "clicked", URL_entry.set_text,
                DEFAULT_ALTERNATE_SEARCH_URL)

            hb.pack_start(l1, False, True, 0)
            hb.pack_start(URL_entry, True, True, 0)
            hb.pack_start(URL_revert, False, True, 0)

            vb2.pack_start(hb, False, True, 0)

            def on_alternate_search_toggled(button, *args):
                self.Conf.alternate_search_enabled = button.get_active()

            alternate_search_enabled = Gtk.CheckButton(
                label=_("Search via above URL if the lyrics "
                        "couldn't be found in LyricsWikia."),
                use_underline=True)
            alternate_search_enabled.set_active(
                self.Conf.alternate_search_enabled)
            alternate_search_enabled.connect("toggled",
                on_alternate_search_toggled)

            vb2.pack_start(alternate_search_enabled, False, True, 0)

            return vb2

        frame = qltk.Frame(label=_("Display"),
            child=build_display_widget())
        frame.set_border_width(6)
        self.pack_start(frame, False, True, 0)

        frame = qltk.Frame(label=_("Alternate search"),
            child=build_alternate_search_widget())
        frame.set_border_width(6)
        self.pack_start(frame, False, True, 0)


class LyricsWindow(EventPlugin):
    PLUGIN_ID = 'lyricswindow'
    PLUGIN_NAME = _('Lyrics Window')
    PLUGIN_DESC = _("Shows a window containing lyrics of the playing song.")
    PLUGIN_ICON = Icons.APPLICATION_INTERNET

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
