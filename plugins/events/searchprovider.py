# Copyright 2013 Christoph Reiter <reiter.christoph@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

"""
For this plugin to work Gnome Shell needs this file:

/usr/share/gnome-shell/search-providers/quodlibet-search-provider.ini

with the following content:

[Shell Search Provider]
DesktopId=quodlibet.desktop
BusName=net.sacredchao.QuodLibet.SearchProvider
ObjectPath=/net/sacredchao/QuodLibet/SearchProvider
Version=2
"""

import os

import dbus
import dbus.service

from quodlibet import app
from quodlibet import util
from quodlibet.util.dbusutils import dbus_unicode_validate
from quodlibet.plugins.events import EventPlugin
from quodlibet.parse import Query
from quodlibet.plugins import PluginImportException


def get_gs_provider_files():
    """Return all installed search provider files for Gnome Shell"""

    ini_files = []
    for d in util.xdg_get_system_data_dirs():
        path = os.path.join(d, "gnome-shell", "search-providers")
        try:
            for entry in os.listdir(path):
                if entry.endswith(".ini"):
                    ini_files.append(os.path.join(path, entry))
        except EnvironmentError:
            pass
    return ini_files


def check_ini_installed():
    """Raise if no Gnome Shell ini file for Quod Libet is found"""

    quodlibet_installed = False
    for path in get_gs_provider_files():
        try:
            with open(path, "rb") as handle:
                if SearchProvider.BUS_NAME in handle.read():
                    quodlibet_installed = True
                    break
        except EnvironmentError:
            pass

    if not quodlibet_installed:
        raise PluginImportException(
            _("No Gnome Shell search provider for "
              "Quod Libet installed."))


class GnomeSearchProvider(EventPlugin):
    PLUGIN_ID = "searchprovider"
    PLUGIN_NAME = _("Gnome Search Provider")
    PLUGIN_DESC = _("Allow the Gnome Shell to search the library")
    PLUGIN_ICON = "gtk-connect"
    PLUGIN_VERSION = "0.1"

    def enabled(self):
        self.obj = SearchProvider()

    def disabled(self):
        self.obj.remove_from_connection()
        del self.obj

        import gc
        gc.collect()


ENTRY_ICON = (". GThemedIcon audio-mpeg gnome-mime-audio-mpeg "
              "audio-x-generic")


def get_song_id(song):
    return str(id(song))


def get_songs_for_ids(library, ids):
    songs = []
    ids = set(ids)
    for song in library:
        song_id = get_song_id(song)
        if song_id in ids:
            songs.append(song)
            ids.discard(song_id)
            if not ids:
                break
    return songs


class SearchProvider(dbus.service.Object):
    PATH = "/net/sacredchao/QuodLibet/SearchProvider"
    BUS_NAME = "net.sacredchao.QuodLibet.SearchProvider"
    IFACE = "org.gnome.Shell.SearchProvider2"

    def __init__(self):
        bus = dbus.SessionBus()
        name = dbus.service.BusName(self.BUS_NAME, bus)
        super(SearchProvider, self).__init__(name, self.PATH)

    @dbus.service.method(IFACE, in_signature="as", out_signature="as")
    def GetInitialResultSet(self, terms):
        if terms:
            query = Query("")
            for term in terms:
                query &= Query(term)
            songs = filter(query.search, app.library)
        else:
            songs = app.library.values()

        ids = [get_song_id(s) for s in songs]
        return ids

    @dbus.service.method(IFACE, in_signature="asas", out_signature="as")
    def GetSubsearchResultSet(self, previous_results, terms):
        query = Query("")
        for term in terms:
            query &= Query(term)

        songs = get_songs_for_ids(app.library, previous_results)
        ids = [get_song_id(s) for s in songs if query.search(s)]
        return ids

    @dbus.service.method(IFACE, in_signature="as",
                         out_signature="aa{sv}")
    def GetResultMetas(self, identifiers):
        metas = []
        for song in get_songs_for_ids(app.library, identifiers):
            name = song("title")
            description = song("~artist~title")
            song_id = get_song_id(song)
            meta = dbus.Dictionary({
                "name": dbus_unicode_validate(name),
                "id": song_id,
                "description": dbus_unicode_validate(description),
                "gicon": ENTRY_ICON,
            }, signature="ss")
            metas.append(meta)

        return metas

    @dbus.service.method(IFACE, in_signature="sasu")
    def ActivateResult(self, identifier, terms, timestamp):
        try:
            app.window.browser.filter_text(" ".join(terms))
        except NotImplementedError:
            pass

        songs = get_songs_for_ids(app.library, [identifier])
        if not songs:
            return

        if app.player.go_to(songs[0], True):
            app.player.paused = False

    @dbus.service.method(IFACE, in_signature="asu")
    def LaunchSearch(self, terms, timestamp):
        try:
            app.window.browser.filter_text(" ".join(terms))
        except NotImplementedError:
            pass
        else:
            app.present()


# the plugin is useless without the ini file...
check_ini_installed()
