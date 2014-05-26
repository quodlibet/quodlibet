# Copyright 2012 Nick Boultbee
#           2012,2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import subprocess

from gi.repository import Gtk

try:
    import dbus
except ImportError:
    class FakeDbus(object):
        def __getattribute__(self, name):
            if name == "DBusException":
                return Exception
            raise Exception
    dbus = FakeDbus()

from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.util.uri import URI
from quodlibet.qltk.msg import ErrorMessage
from quodlibet.util.dprint import print_d
from quodlibet.util.path import is_fsnative, normalize_path


def get_startup_id():
    from quodlibet import app
    app_name = type(app.window).__name__
    return "%s_TIME%d" % (app_name, Gtk.get_current_event_time())


# http://www.freedesktop.org/wiki/Specifications/file-manager-interface
FDO_PATH = "/org/freedesktop/FileManager1"
FDO_NAME = "org.freedesktop.FileManager1"
FDO_IFACE = "org.freedesktop.FileManager1"


def browse_folders_fdo(songs):
    bus = dbus.SessionBus()
    bus_object = bus.get_object(FDO_NAME, FDO_PATH)
    bus_iface = dbus.Interface(bus_object, dbus_interface=FDO_IFACE)
    uris = map(URI.frompath, set([s("~dirname") for s in songs]))
    bus_iface.ShowFolders(uris, get_startup_id())


def browse_files_fdo(songs):
    bus = dbus.SessionBus()
    bus_object = bus.get_object(FDO_NAME, FDO_PATH)
    bus_iface = dbus.Interface(bus_object, dbus_interface=FDO_IFACE)
    uris = [s("~uri") for s in songs]
    bus_iface.ShowItems(uris, get_startup_id())


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
        bus_iface.DisplayFolder(uri, display, get_startup_id())


def browse_files_thunar(songs, display=""):
    bus = dbus.SessionBus()
    bus_object = bus.get_object(XFCE_NAME, XFCE_PATH)
    bus_iface = dbus.Interface(bus_object, dbus_interface=XFCE_IFACE)
    for song in songs:
        dirname = song("~dirname")
        basename = song("~basename")
        bus_iface.DisplayFolderAndSelect(URI.frompath(dirname), basename,
                                         display, get_startup_id())


def browse_folders_gnome_open(songs):
    dirs = list(set([s("~dirname") for s in songs]))
    for dir_ in dirs:
        if subprocess.call(["gnome-open", dir_]) != 0:
            raise EnvironmentError


def browse_folders_xdg_open(songs):
    dirs = list(set([s("~dirname") for s in songs]))
    for dir_ in dirs:
        if subprocess.call(["xdg-open", dir_]) != 0:
            raise EnvironmentError


def show_files_win32(path, files):
    """Takes a path to a directory and a list of filenames in that directory
    to display.
    """

    assert os.name == "nt"

    import pywintypes
    from win32com.shell import shell

    assert is_fsnative(path)
    assert all(is_fsnative(f) for f in files)

    normalized_files = map(normalize_path, files)

    try:
        folder_pidl = shell.SHILCreateFromPath(path, 0)[0]
        desktop = shell.SHGetDesktopFolder()
        shell_folder = desktop.BindToObject(
            folder_pidl, None, shell.IID_IShellFolder)
        items = []
        for item in shell_folder:
            name = desktop.GetDisplayNameOf(item, 0)
            if normalize_path(name) in normalized_files:
                items.append(item)
        shell.SHOpenFolderAndSelectItems(folder_pidl, items, 0)
    except pywintypes.com_error:
        return


def group_files(file_paths):
    """Groups a sequence of absolute file paths into their dirname and a
    list of entry names.

    The entry order is the same as with the passed in paths.
    """

    dirs = {}
    for p in file_paths:
        assert os.path.isabs(p)
        dirname = os.path.dirname(p)
        basename = os.path.basename(p)
        dirs.setdefault(dirname, []).append(basename)
    return dirs


def browse_files_win_explorer(songs):
    file_paths = [song("~filename") for song in songs]
    for path, names in group_files(file_paths).items():
        show_files_win32(path, names)


def browse_folders_win_explorer(songs):
    # as an added bonus, this also selects the files in the folders
    browse_files_win_explorer(songs)


class HandlingMixin(object):
    def plugin_handles(self, songs):
        # By default, any single song being a file is good enough
        for song in songs:
            if song.is_file:
                return True
        return False

    def handle(self, songs):
        """
        Uses the first successful handler in callable list `_HANDLERS`
        to handle `songs`
        Returns False if none could be used
        """
        if not hasattr(self, "_HANDLERS"):
            return False
        for handler in self._HANDLERS:
            name = handler.__name__
            try:
                print_d("Trying %r..." % name)
                handler(songs)
            except (dbus.DBusException, EnvironmentError):
                print_d("...failed.")
                # TODO: caching of failures (re-order list maybe)
            else:
                print_d("...success!")
                return True
        print_d("No handlers could be used.")
        return False


class BrowseFolders(SongsMenuPlugin, HandlingMixin):
    PLUGIN_ID = 'Browse Folders'
    PLUGIN_NAME = _('Browse Folders')
    PLUGIN_DESC = "View the songs' folders in a file manager"
    PLUGIN_ICON = Gtk.STOCK_OPEN
    PLUGIN_VERSION = '1.1'

    _HANDLERS = [browse_folders_fdo, browse_folders_thunar,
                 browse_folders_xdg_open, browse_folders_gnome_open,
                 browse_folders_win_explorer]

    def plugin_songs(self, songs):
        songs = [s for s in songs if s.is_file]
        print_d("Trying to browse folders...")
        if not self.handle(songs):
            ErrorMessage(self.plugin_window,
                         _("Unable to open folders"),
                         _("No program available to open folders.")).run()


class BrowseFiles(SongsMenuPlugin, HandlingMixin):
    PLUGIN_ID = 'Browse Files'
    PLUGIN_NAME = _('Show File')
    PLUGIN_DESC = "View the song's file in a file manager"
    PLUGIN_ICON = Gtk.STOCK_OPEN
    PLUGIN_VERSION = '1.1'

    _HANDLERS = [browse_files_fdo, browse_files_thunar,
                 browse_files_win_explorer]

    def plugin_single_song(self, song):
        songs = [s for s in [song] if s.is_file]
        print_d("Trying to browse files...")
        if not self.handle(songs):
            ErrorMessage(self.plugin_window,
                         _("Unable to browse files"),
                         _("No program available to browse files.")).run()
