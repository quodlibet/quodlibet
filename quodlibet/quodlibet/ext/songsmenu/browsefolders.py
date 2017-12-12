# -*- coding: utf-8 -*-
# Copyright 2012,2016 Nick Boultbee
#           2012,2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import sys
import subprocess

from gi.repository import Gtk
from senf import fsn2uri, fsnative

from quodlibet.plugins.songshelpers import any_song, is_a_file

try:
    import dbus
except ImportError:
    dbus = None

from quodlibet import _
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.qltk.msg import ErrorMessage
from quodlibet.qltk import Icons
from quodlibet.util.dprint import print_d


class BrowseError(Exception):
    pass


def group_songs(songs):
    """Groups a sequence of songs per dirname.

    The value order is the same as with the passed in songs.
    """

    dirs = {}
    for s in songs:
        dirs.setdefault(s("~dirname"), []).append(s)
    return dirs


def get_startup_id():
    from quodlibet import app
    app_name = type(app.window).__name__
    return "%s_TIME%d" % (app_name, Gtk.get_current_event_time())


def browse_folders_fdo(songs):
    # http://www.freedesktop.org/wiki/Specifications/file-manager-interface
    FDO_PATH = "/org/freedesktop/FileManager1"
    FDO_NAME = "org.freedesktop.FileManager1"
    FDO_IFACE = "org.freedesktop.FileManager1"

    if not dbus:
        raise BrowseError("no dbus")

    try:
        bus = dbus.SessionBus()
        bus_object = bus.get_object(FDO_NAME, FDO_PATH)
        bus_iface = dbus.Interface(bus_object, dbus_interface=FDO_IFACE)

        # open each folder and select the first file we have selected
        for dirname, sub_songs in group_songs(songs).items():
            bus_iface.ShowItems([sub_songs[0]("~uri")], get_startup_id())
    except dbus.DBusException as e:
        raise BrowseError(e)


def browse_folders_thunar(songs, display=""):
    # http://git.xfce.org/xfce/thunar/tree/thunar/thunar-dbus-service-infos.xml
    XFCE_PATH = "/org/xfce/FileManager"
    XFCE_NAME = "org.xfce.FileManager"
    XFCE_IFACE = "org.xfce.FileManager"

    if not dbus:
        raise BrowseError("no dbus")

    try:
        bus = dbus.SessionBus()
        bus_object = bus.get_object(XFCE_NAME, XFCE_PATH)
        bus_iface = dbus.Interface(bus_object, dbus_interface=XFCE_IFACE)

        # open each folder and select the first file we have selected
        for dirname, sub_songs in group_songs(songs).items():
            bus_iface.DisplayFolderAndSelect(
                fsn2uri(dirname),
                sub_songs[0]("~basename"),
                display,
                get_startup_id())
    except dbus.DBusException as e:
        raise BrowseError(e)


def browse_folders_gnome_open(songs):
    try:
        for dir_ in group_songs(songs).keys():
            if subprocess.call(["gnome-open", dir_]) != 0:
                raise EnvironmentError("gnome-open error return status")
    except EnvironmentError as e:
        raise BrowseError(e)


def browse_folders_xdg_open(songs):
    try:
        for dir_ in group_songs(songs).keys():
            if subprocess.call(["xdg-open", dir_]) != 0:
                raise EnvironmentError("xdg-open error return status")
    except EnvironmentError as e:
        raise BrowseError(e)


def show_files_win32(path, files):
    """Takes a path to a directory and a list of filenames in that directory
    to display.

    Returns True on success.
    """

    assert os.name == "nt"
    assert isinstance(path, fsnative)
    assert all(isinstance(f, fsnative) for f in files)

    from quodlibet.util.windows import open_folder_and_select_items

    try:
        open_folder_and_select_items(path, files)
    except WindowsError:
        return False
    return True


def browse_folders_win_explorer(songs):
    if os.name != "nt":
        raise BrowseError("windows only")

    for path, sub_songs in group_songs(songs).items():
        if not show_files_win32(path, [s("~basename") for s in sub_songs]):
            raise BrowseError


def browse_folders_finder(songs):
    if sys.platform != "darwin":
        raise BrowseError("OS X only")

    try:
        for dir_ in group_songs(songs).keys():
            if subprocess.call(["open", "-R", dir_]) != 0:
                raise EnvironmentError("open error return status")
    except EnvironmentError as e:
        raise BrowseError(e)


class BrowseFolders(SongsMenuPlugin):
    PLUGIN_ID = 'Browse Folders'
    PLUGIN_NAME = _('Browse Folders')
    PLUGIN_DESC = _("Opens the songs' folders in a file manager.")
    PLUGIN_ICON = Icons.DOCUMENT_OPEN

    _HANDLERS = [browse_folders_fdo, browse_folders_thunar,
                 browse_folders_xdg_open, browse_folders_gnome_open,
                 browse_folders_win_explorer, browse_folders_finder]

    def plugin_songs(self, songs):
        songs = [s for s in songs if s.is_file]
        print_d("Trying to browse folders...")
        if not self._handle(songs):
            ErrorMessage(self.plugin_window,
                         _("Unable to open folders"),
                         _("No program available to open folders.")).run()

    plugin_handles = any_song(is_a_file)
    """By default, any single song being a file is good enough"""

    def _handle(self, songs):
        """
        Uses the first successful handler in callable list `_HANDLERS`
        to handle `songs`
        Returns False if none could be used
        """

        for handler in self._HANDLERS:
            name = handler.__name__
            try:
                print_d("Trying %r..." % name)
                handler(songs)
            except BrowseError as e:
                print_d("...failed: %r" % e)
            else:
                print_d("...success!")
                return True
        print_d("No handlers could be used.")
        return False
