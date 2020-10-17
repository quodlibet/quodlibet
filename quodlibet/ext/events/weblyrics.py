# Copyright 2014 Christoph Reiter
#           2015 Joschua Gandert
#           2017 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import threading
from xml.dom import minidom
from urllib.parse import quote
import queue

from quodlibet import _, print_d
from quodlibet.plugins.gui import UserInterfacePlugin
from quodlibet.util import gi_require_versions, is_windows, is_osx
from quodlibet.plugins.events import EventPlugin
from quodlibet.plugins import (PluginImportException, PluginConfig, ConfProp,
    BoolConfProp, FloatConfProp, PluginNotSupportedError)

try:
    gi_require_versions("WebKit2", ["4.0", "3.0"])
except ValueError as e:
    if is_windows() or is_osx():
        raise PluginNotSupportedError
    raise PluginImportException("GObject Introspection: " + str(e))

from gi.repository import WebKit2, Gtk, GLib

from quodlibet import qltk
from quodlibet.util import escape, cached_property, connect_obj
from quodlibet.qltk import Icons, Align
from quodlibet.qltk.entry import UndoEntry
from quodlibet.pattern import URLFromPattern
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
        super().__init__()
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


class LyricsWebView(Gtk.ScrolledWindow):

    def __init__(self, conf):
        print_d("Creating Lyrics web view")
        super().__init__()
        self.conf = conf

        self._thread = LyricsWikiaSearchThread()
        self.connect("destroy", lambda *x: self._thread.stop())

        self.current_song = None
        self._reload_web_view()

    def _reload_web_view(self, web_view=None):
        if web_view is not None:
            self.remove(web_view)

        self._view = view = WebKit2.WebView()
        self.set_zoom_level(self.conf.zoom_level)

        # stop alert windows
        view.connect('script-dialog', lambda *args: True)

        view.connect('web-process-crashed', self._reload_web_view)

        settings = view.get_settings()
        settings.set_property("user-agent", USER_AGENT)
        settings.set_media_playback_requires_user_gesture(True)

        def scroll_to_lyrics(view, load_event):
            if load_event != WebKit2.LoadEvent.COMMITTED:
                return
            view.run_javascript("""
                document.addEventListener('DOMContentLoaded', function() {
                    var box = document.getElementsByClassName('lyricbox')[0];
                    box.scrollIntoView(true);
                }, false);
            """, None, None, None)

        view.connect('load-changed', scroll_to_lyrics)

        self.add(view)
        self.show_all()

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
        else:
            self._view.load_uri(page)


def get_config(prefix):
    class LyricsWindowConfig:

        plugin_conf = PluginConfig(prefix)

        alternate_search_url = ConfProp(plugin_conf, "alternate_search_url",
            DEFAULT_ALTERNATE_SEARCH_URL)
        alternate_search_enabled = BoolConfProp(plugin_conf,
            "alternate_search_enabled", True)
        zoom_level = FloatConfProp(plugin_conf, "zoom_level", 1.4)

    return LyricsWindowConfig()


class ConfigLabel(Gtk.Label):
    """Customised Label for configuration, tied to a widget"""

    def __init__(self, text, widget):
        super().__init__(label=text, use_underline=True)
        self.set_mnemonic_widget(widget)
        self.set_alignment(0.0, 0.5)


class LyricsWindowPrefs(Gtk.VBox):

    def __init__(self, plugin):
        super().__init__(spacing=6)

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

                pane = self.plugin._pane
                if pane is not None:
                    pane.set_zoom_level(value)

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


class WebLyrics(EventPlugin, UserInterfacePlugin):
    PLUGIN_ID = 'WebLyrics'
    CONFIG_SECTION = "lyricswindow"
    PLUGIN_NAME = _('Web Lyrics')
    PLUGIN_DESC = _("Shows a sidebar containing online lyrics "
                    "of the playing song.")
    PLUGIN_ICON = Icons.APPLICATION_INTERNET

    _pane = None

    def _destroy(self, *args):
        self._pane = None

    def enabled(self):
        if self._pane is None:
            self._pane = self._create_sw()

    @cached_property
    def Conf(self):
        return get_config(self.CONFIG_SECTION)

    def PluginPreferences(self, parent):
        return LyricsWindowPrefs(self)

    def _create_sw(self):
        sw = LyricsWebView(self.Conf)
        sw.show()
        sw.connect("destroy", self._destroy)
        return sw

    def create_sidebar(self):
        return Align(self._pane)

    def plugin_on_song_started(self, song):
        pane = self._pane
        if pane is not None:
            pane.set_song(song)
