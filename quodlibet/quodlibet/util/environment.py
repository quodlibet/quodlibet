# -*- coding: utf-8 -*-
# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

"""Varisour function for figuring out which platform wa are running on
and under which environment.
"""

import os
import sys


def _dbus_name_owned(name):
    """Returns True if the dbus name has an owner"""

    if not is_linux():
        return False

    try:
        import dbus
    except ImportError:
        return False

    try:
        bus = dbus.Bus(dbus.Bus.TYPE_SESSION)
        return bus.name_has_owner(name)
    except dbus.DBusException:
        return False


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

    return is_windows() and "WINEDEBUG" in os.environ


def is_osx():
    """If we are running under OS X"""

    return sys.platform == "darwin"


def is_py2exe():
    """If we are running under py2exe"""

    return is_windows() and hasattr(sys, "frozen")


def is_py2exe_console():
    """If we are running under py2exe in console mode"""

    return is_py2exe() and sys.frozen == "console_exe"


def is_py2exe_window():
    """If we are running under py2exe in window mode"""

    return is_py2exe() and not is_py2exe_console()
