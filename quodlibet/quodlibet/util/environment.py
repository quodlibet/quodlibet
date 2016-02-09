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


def xdg_get_current_desktop():
    """Returns a list of values present in XDG_CURRENT_DESKTOP

    https://www.freedesktop.org/software/systemd/man/pam_systemd.html
    """

    value = os.environ.get("XDG_CURRENT_DESKTOP", "")
    if not value:
        return []
    return value.split(":")


def is_kde():
    """If we are running under KDE/plasma"""

    return "KDE" in xdg_get_current_desktop()


def is_unity():
    """If we are running under Ubuntu/Unity"""

    return "Unity" in xdg_get_current_desktop()


def is_windows():
    """If we are running under Windows or Wine"""

    return os.name == "nt"


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
