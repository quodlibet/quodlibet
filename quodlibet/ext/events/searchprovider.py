# Copyright 2013 Christoph Reiter <reiter.christoph@gmail.com>
#           2024 Nick Boultbee
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
For this plugin to work GNOME Shell needs this file:

/usr/share/gnome-shell/search-providers/io.github.quodlibet.QuodLibet-search-provider.ini
(or in a similar XDG directory)

A copy of this file can be found in ../../../data/
"""

import os
import sys
from pathlib import Path
from collections.abc import Collection

from quodlibet.util.thumbnails import get_thumbnail, get_cache_info

if os.name == "nt" or sys.platform == "darwin":
    from quodlibet.plugins import PluginNotSupportedError

    raise PluginNotSupportedError

from gi.repository import GLib
from gi.repository import Gio

from quodlibet import _, print_d
from quodlibet import app
from quodlibet.util.dbusutils import dbus_unicode_validate
from quodlibet.plugins.events import EventPlugin
from quodlibet.query import Query
from quodlibet.plugins import PluginImportError
from quodlibet.util.path import xdg_get_system_data_dirs
from quodlibet.qltk import Icons

DEFAULT_SEARCH_PROVIDER_DIR = "/usr/share/gnome-shell/search-providers"
THUMBNAIL_SIZE = (256, 256)


def get_gs_provider_files() -> Collection[Path]:
    """Return all installed search provider files for GNOME Shell"""

    ini_files = []
    for d in xdg_get_system_data_dirs():
        path = Path(d) / "gnome-shell" / "search-providers"
        try:
            for entry in os.listdir(path):
                if entry.endswith(".ini"):
                    ini_files.append(path / entry)
        except OSError:
            pass
    return ini_files


def check_ini_installed():
    """Raise if no GNOME Shell ini file for Quod Libet is found"""

    provider_installed = False
    for path in get_gs_provider_files():
        try:
            with open(path, "rb") as handle:
                data = handle.read().decode("utf-8", "replace")
                if SearchProvider.BUS_NAME in data:
                    provider_installed = True
                    break
        except OSError:
            pass

    if not provider_installed:
        path = DEFAULT_SEARCH_PROVIDER_DIR
        msg = (
            _("No GNOME Shell search provider for Quod Libet installed.")
            + " \n"
            + _("Have you copied the ini file to %s (or similar)?") % path
        )
        raise PluginImportError(msg)


class GnomeSearchProvider(EventPlugin):
    PLUGIN_ID = "searchprovider"
    PLUGIN_NAME = _("GNOME Search Provider")
    PLUGIN_DESC = _("Allows GNOME Shell to search the library.")
    PLUGIN_ICON = Icons.SYSTEM_SEARCH

    def enabled(self):
        self.obj = SearchProvider()

    def disabled(self):
        self.obj.remove_from_connection()
        del self.obj

        import gc

        gc.collect()


ENTRY_ICON = ". GThemedIcon audio-mpeg gnome-mime-audio-mpeg audio-x-generic"


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
    print_d(f"Got {len(songs)} songs matching {ids}")
    return songs


class SearchProvider:
    """
    <!DOCTYPE node PUBLIC
     '-//freedesktop//DTD D-BUS Object Introspection 1.0//EN'
     'http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd'>
    <node name="/io/github/quodlibet/QuodLibet/SearchProvider">
      <interface name="org.freedesktop.DBus.Introspectable">
        <method name="Introspect">
          <arg direction="out" type="s" />
        </method>
      </interface>
      <interface name="org.gnome.Shell.SearchProvider2">
        <method name="GetInitialResultSet">
          <arg direction="in"  type="as" name="terms" />
          <arg direction="out" type="as" name="results" />
        </method>
        <method name="GetSubsearchResultSet">
          <arg direction="in"  type="as" name="previous_results" />
          <arg direction="in"  type="as" name="terms" />
          <arg direction="out" type="as" name="results" />
        </method>
        <method name="GetResultMetas">
          <arg direction="in"  type="as" name="identifiers" />
          <arg direction="out" type="aa{sv}" name="metas" />
        </method>
        <method name="ActivateResult">
          <arg direction="in"  type="s" name="identifier" />
          <arg direction="in"  type="as" name="terms" />
          <arg direction="in"  type="u" name="timestamp" />
        </method>
        <method name="LaunchSearch">
          <arg direction="in"  type="as" name="terms" />
          <arg direction="in"  type="u" name="timestamp" />
        </method>
      </interface>
    </node>
    """

    PATH = "/io/github/quodlibet/QuodLibet/SearchProvider"
    BUS_NAME = "io.github.quodlibet.QuodLibet.SearchProvider"
    IFACE = "org.gnome.Shell.SearchProvider2"

    def __init__(self):
        self._own_id = Gio.bus_own_name(
            Gio.BusType.SESSION,
            self.BUS_NAME,
            Gio.BusNameOwnerFlags.NONE,
            self.on_bus_acquired,
            None,
            self.on_name_lost,
        )
        self._registered_ids = []
        self._method_outargs = {}

    def on_bus_acquired(self, connection, name):
        info = Gio.DBusNodeInfo.new_for_xml(self.__doc__)
        for interface in info.interfaces:
            for method in interface.methods:
                self._method_outargs[method.name] = "({})".format(
                    "".join([arg.signature for arg in method.out_args])
                )

            _id = connection.register_object(
                object_path=self.PATH,
                interface_info=interface,
                method_call_closure=self.on_method_call,
            )
            self._registered_ids.append(_id)

    def on_name_lost(self, connection, name):
        for _id in self._registered_ids:
            connection.unregister_object(_id)

    def remove_from_connection(self):
        if self._own_id is not None:
            Gio.bus_unown_name(self._own_id)
            self._own_id = None

    def on_method_call(
        self,
        connection,
        sender,
        object_path,
        interface_name,
        method_name,
        parameters,
        invocation,
    ):
        args = list(parameters.unpack())
        result = getattr(self, method_name)(*args)
        if not isinstance(result, tuple):
            result = (result,)

        out_args = self._method_outargs[method_name]
        if out_args != "()":
            variant = GLib.Variant(out_args, result)
            invocation.return_value(variant)
        else:
            invocation.return_value(None)

    def Introspect(self):
        return self.__doc__

    def GetInitialResultSet(self, terms):
        print_d(f"Getting initial result set for {terms}")
        if terms:
            query = Query("")
            for term in terms:
                query &= Query(term)
            songs = filter(query.search, app.library)
        else:
            songs = app.library.values()

        return [get_song_id(s) for s in songs]

    def GetSubsearchResultSet(self, previous_results, terms):
        # Eager searching-as-you-type in Gnome makes this useless it seems,
        # so just use the full terms each time.
        return self.GetInitialResultSet(terms)

    def GetResultMetas(self, identifiers):
        print_d(f"Getting result metas for {identifiers}")
        metas = []
        for song in get_songs_for_ids(app.library, identifiers):
            name = song("title")
            description = song.comma("~people")
            song_id = get_song_id(song)
            cover = app.cover_manager.get_cover(song)
            if cover:
                # We need a permanent-ish copy of this for DBus clients
                get_thumbnail(cover.name, THUMBNAIL_SIZE, ignore_temp=False)
                p = get_cache_info(Path(cover.name), THUMBNAIL_SIZE)[0]
                gicon = str(p)
            else:
                gicon = ENTRY_ICON
            meta = {
                "name": GLib.Variant("s", dbus_unicode_validate(name)),
                "id": GLib.Variant("s", song_id),
                "description": GLib.Variant("s", dbus_unicode_validate(description)),
                "gicon": GLib.Variant("s", gicon),
            }
            metas.append(meta)

        return metas

    def ActivateResult(self, identifier, terms, timestamp):
        songs = get_songs_for_ids(app.library, [identifier])
        if not songs:
            return

        if app.player.go_to(songs[0], True):
            app.player.paused = False

    def LaunchSearch(self, terms, timestamp):
        try:
            app.window.browser.filter_text(" ".join(terms))
        except NotImplementedError:
            pass
        else:
            app.present()


# the plugin is useless without the ini file...
check_ini_installed()
