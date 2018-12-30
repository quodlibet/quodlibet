# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Varisour function for figuring out which platform wa are running on
and under which environment.
"""

import os
import sys
import ctypes

from gi.repository import GLib, Gio


def _dbus_name_owned(name):
    """Returns True if the dbus name has an owner"""

    if not is_linux():
        return False

    return dbus_name_owned(name)


def is_flatpak():
    """If we are running in a flatpak"""

    return is_linux() and os.path.exists("/.flatpak-info")


def is_plasma():
    """If we are running under plasma"""

    return _dbus_name_owned("org.kde.plasmashell")


def is_unity():
    """If we are running under Ubuntu/Unity"""

    return _dbus_name_owned("com.canonical.Unity.Launcher")


def is_enlightenment():
    """If we are running under Enlightenment"""

    return _dbus_name_owned("org.enlightenment.wm.service")


def is_linux():
    """If we are on Linux (or similar)"""

    return not is_windows() and not is_osx()


def is_windows():
    """If we are running under Windows or Wine"""

    return os.name == "nt"


def is_wine():
    """If we are running under Wine"""

    if not is_windows():
        return False

    try:
        ctypes.cdll.ntdll.wine_get_version
    except AttributeError:
        return False
    else:
        return True


def is_osx():
    """If we are running under OS X"""

    return sys.platform == "darwin"


def dbus_name_owned(name):
    """Returns True if the dbus name has an owner"""

    BUS_DAEMON_NAME = 'org.freedesktop.DBus'
    BUS_DAEMON_PATH = '/org/freedesktop/DBus'
    BUS_DAEMON_IFACE = 'org.freedesktop.DBus'

    try:
        bus = Gio.DBusProxy.new_for_bus_sync(
            Gio.BusType.SESSION, Gio.DBusProxyFlags.NONE, None,
            BUS_DAEMON_NAME, BUS_DAEMON_PATH, BUS_DAEMON_IFACE, None)
        return bus.NameHasOwner('(s)', name)
    except GLib.Error:
        return False
