# -*- coding: utf-8 -*-
# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import sys
import locale
from functools import wraps

from . import windows


if os.name == "nt":
    environ = windows.WindowsEnviron()
else:
    environ = os.environ
"""
An environ dict which contains unicode under Windows and str everywhere else
"""


if os.name == "nt":
    argv = windows.get_win32_unicode_argv()
else:
    argv = sys.argv
"""
An argv list which contains unicode under Windows and str everywhere else
"""


def cached_func(f):
    """Decorator which caches the return value of a function which
    doesn't take any input.
    """

    res = []

    @wraps(f)
    def wrapper():
        if not res:
            res.append(f())
        return res[0]
    return wrapper


def _verify_encoding(encoding):
    try:
        u"".encode(encoding)
    except LookupError:
        encoding = "utf-8"
    return encoding


@cached_func
def get_locale_encoding():
    """Returns the encoding defined by the locale"""

    try:
        encoding = locale.getpreferredencoding()
    except locale.Error:
        encoding = "utf-8"
    else:
        # python on macports can return a bugs result (empty string)
        encoding = _verify_encoding(encoding)

    return encoding


@cached_func
def get_fs_encoding():
    """Returns the encoding used for paths by glib."""

    if os.name == "nt":
        return "utf-8"

    # https://developer.gnome.org/glib/stable/glib-running.html
    if "G_FILENAME_ENCODING" in os.environ:
        fscoding = os.environ["G_FILENAME_ENCODING"].split(",")[0]
        if fscoding == "@locale":
            fscoding = get_locale_encoding()
        return _verify_encoding(fscoding)
    elif "G_BROKEN_FILENAMES" in os.environ:
        return get_locale_encoding()
    else:
        return "utf-8"
