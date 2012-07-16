# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import subprocess

import gtk
import dbus

from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.util.uri import URI
from quodlibet.qltk.msg import ErrorMessage


STARTUP_ID = "quodlibet"  # TODO: figure out what to do about the startup spec


# http://www.freedesktop.org/wiki/Specifications/file-manager-interface
FDO_PATH = "/org/freedesktop/FileManager1"
FDO_NAME = "org.freedesktop.FileManager1"
FDO_IFACE = "org.freedesktop.FileManager1"


def browse_folders_fdo(songs):
    bus = dbus.SessionBus()
    bus_object = bus.get_object(FDO_NAME, FDO_PATH)
    bus_iface = dbus.Interface(bus_object, dbus_interface=FDO_IFACE)
    uris = map(URI.frompath, set([s("~dirname") for s in songs]))
    bus_iface.ShowFolders(uris, STARTUP_ID)


def browse_files_fdo(songs):
    bus = dbus.SessionBus()
    bus_object = bus.get_object(FDO_NAME, FDO_PATH)
    bus_iface = dbus.Interface(bus_object, dbus_interface=FDO_IFACE)
    uris = [s("~uri") for s in songs]
    bus_iface.ShowItems(uris, STARTUP_ID)


# http://git.xfce.org/xfce/thunar/tree/thunar/thunar-dbus-service-infos.xml
XFCE_PATH = "/org/xfce/FileManager"
XFCE_NAME = "org.xfce.FileManager"
XFCE_IFACE = "org.xfce.FileManager"


def browse_folders_thunar(songs, display=""):
    bus = dbus.SessionBus()
    bus_object = bus.get_object(XFCE_NAME, XFCE_PATH)
    bus_iface = dbus.Interface(bus_object, dbus_interface=XFCE_IFACE)
    uris = map(URI.frompath, set([s("~dirname") for s in songs]))
    for uri in uris:
        bus_iface.DisplayFolder(uri, display, STARTUP_ID)


def browse_files_thunar(songs, display=""):
    bus = dbus.SessionBus()
    bus_object = bus.get_object(XFCE_NAME, XFCE_PATH)
    bus_iface = dbus.Interface(bus_object, dbus_interface=XFCE_IFACE)
    for song in songs:
        dirname = song("~dirname")
        basename = song("~basename")
        bus_iface.DisplayFolderAndSelect(URI.frompath(dirname), basename,
                                         display, STARTUP_ID)


def browse_folders_gnome_open(songs, callback=None):
    dirs = list(set([s("~dirname") for s in songs]))
    for dir_ in dirs:
        if subprocess.call(["gnome-open", dir_]) != 0:
            raise EnvironmentError


def browse_folders_xdg_open(songs, callback=None):
    dirs = list(set([s("~dirname") for s in songs]))
    for dir_ in dirs:
        if subprocess.call(["xdg-open", dir_]) != 0:
            raise EnvironmentError


class BrowseFolters(SongsMenuPlugin):
    PLUGIN_ID = 'Browse Folders'
    PLUGIN_NAME = _('Browse Folders')
    PLUGIN_DESC = "View the songs' folders in a file manager"
    PLUGIN_ICON = gtk.STOCK_OPEN
    PLUGIN_VERSION = '1'

    _HANDLERS = [browse_folders_fdo, browse_folders_thunar,
                 browse_folders_xdg_open, browse_folders_gnome_open]

    def plugin_songs(self, songs):
        print_d("Try to browse folders")
        for handler in self._HANDLERS:
            name = handler.__name__
            try:
                print_d("Try %r" % name)
                handler(songs)
            except (dbus.DBusException, EnvironmentError):
                print_d("%r failed" % name)
                pass
            else:
                print_d("OK")
                return

        ErrorMessage(self.plugin_window,
                     _("Unable to open folders"),
                     _("No program available to open folders.")).run()


class BrowseFiles(SongsMenuPlugin):
    PLUGIN_ID = 'Browse Files'
    PLUGIN_NAME = _('Browse File')
    PLUGIN_DESC = "View the songs' files in a file manager"
    PLUGIN_ICON = gtk.STOCK_OPEN
    PLUGIN_VERSION = '1'

    _HANDLERS = [browse_files_fdo, browse_files_thunar]

    # TODO: switch to plugin_songs if nautilus/thunar handle multiselection
    def plugin_single_song(self, song):
        songs = [song]

        print_d("Try to browse files")
        for handler in self._HANDLERS:
            name = handler.__name__
            try:
                print_d("Try %r" % name)
                handler(songs)
            except (dbus.DBusException, EnvironmentError):
                print_d("%r failed" % name)
                pass
            else:
                print_d("OK")
                return

        ErrorMessage(self.plugin_window,
                     _("Unable to browse files"),
                     _("No program available to browse files.")).run()
