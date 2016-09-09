# -*- coding: utf-8 -*-
# Copyright 2004-2009 Joe Wreschnig, Michael Urman, Steven Robertson
#           2011-2013 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import re
import sys
import errno
import tempfile
import codecs
import shlex
import urllib

from senf import fsnative, bytes2fsn, fsn2bytes, expanduser, sep, expandvars

from quodlibet.compat import PY2, urlparse
from . import windows
from .misc import environ

if sys.platform == "darwin":
    from Foundation import NSString


def mkdir(dir_, *args):
    """Make a directory, including all its parent directories. This does not
    raise an exception if the directory already exists (and is a
    directory)."""

    try:
        os.makedirs(dir_, *args)
    except OSError as e:
        if e.errno != errno.EEXIST or not os.path.isdir(dir_):
            raise


def glib2fsn(path):
    """Takes a glib filename and returns a fsnative path"""

    if PY2:
        return bytes2fsn(path, "utf-8")
    else:
        return path


def fsn2glib(path):
    """Takes a fsnative path and returns a glib filename"""

    if PY2:
        return fsn2bytes(path, "utf-8")
    else:
        return path


def iscommand(s):
    """True if an executable file `s` exists in the user's path, or is a
    fully qualified and existing executable file."""

    if s == "" or os.path.sep in s:
        return os.path.isfile(s) and os.access(s, os.X_OK)
    else:
        s = s.split()[0]
        path = environ.get('PATH', '') or os.defpath
        for p in path.split(os.path.pathsep):
            p2 = os.path.join(p, s)
            if os.path.isfile(p2) and os.access(p2, os.X_OK):
                return True
        else:
            return False


def listdir(path, hidden=False):
    """List files in a directory, sorted, fully-qualified.

    If hidden is false, Unix-style hidden files are not returned.
    """

    assert isinstance(path, fsnative)

    if hidden:
        filt = None
    else:
        filt = lambda base: not base.startswith(".")
    if path.endswith(os.sep):
        join = "".join
    else:
        join = os.sep.join
    return [join([path, basename])
            for basename in sorted(os.listdir(path))
            if filt(basename)]


def mtime(filename):
    """Return the mtime of a file, or 0 if an error occurs."""
    try:
        return os.path.getmtime(filename)
    except OSError:
        return 0


def filesize(filename):
    """Return the size of a file, or 0 if an error occurs."""
    try:
        return os.path.getsize(filename)
    except OSError:
        return 0


def escape_filename(s):
    """Escape a string in a manner suitable for a filename.

    Takes unicode or str and returns a fsnative path.
    """

    if isinstance(s, unicode):
        s = s.encode("utf-8")

    return fsnative(urllib.quote(s, safe="").decode("utf-8"))


def unescape_filename(s):
    """Unescape a string in a manner suitable for a filename."""
    if isinstance(s, unicode):
        s = s.encode("utf-8")
    return urllib.unquote(s).decode("utf-8")


def unexpand(filename, HOME=expanduser("~")):
    """Replace the user's home directory with ~/, if it appears at the
    start of the path name."""
    sub = (os.name == "nt" and "%USERPROFILE%") or "~"
    if filename == HOME:
        return sub
    elif filename.startswith(HOME + os.path.sep):
        filename = filename.replace(HOME, sub, 1)
    return filename


def find_mount_point(path):
    while not os.path.ismount(path):
        path = os.path.dirname(path)
    return path


def xdg_get_system_data_dirs():
    """http://standards.freedesktop.org/basedir-spec/latest/"""

    if os.name == "nt":
        from gi.repository import GLib
        dirs = []
        for dir_ in GLib.get_system_data_dirs():
            dirs.append(glib2fsn(dir_))
        return dirs

    data_dirs = os.getenv("XDG_DATA_DIRS")
    if data_dirs:
        return map(os.path.abspath, data_dirs.split(":"))
    else:
        return ("/usr/local/share/", "/usr/share/")


def xdg_get_cache_home():
    if os.name == "nt":
        from gi.repository import GLib
        return glib2fsn(GLib.get_user_cache_dir())

    data_home = os.getenv("XDG_CACHE_HOME")
    if data_home:
        return os.path.abspath(data_home)
    else:
        return os.path.join(os.path.expanduser("~"), ".cache")


def xdg_get_data_home():
    if os.name == "nt":
        from gi.repository import GLib
        return glib2fsn(GLib.get_user_data_dir())

    data_home = os.getenv("XDG_DATA_HOME")
    if data_home:
        return os.path.abspath(data_home)
    else:
        return os.path.join(os.path.expanduser("~"), ".local", "share")


def xdg_get_config_home():
    if os.name == "nt":
        from gi.repository import GLib
        return glib2fsn(GLib.get_user_config_dir())

    data_home = os.getenv("XDG_CONFIG_HOME")
    if data_home:
        return os.path.abspath(data_home)
    else:
        return os.path.join(os.path.expanduser("~"), ".config")


def parse_xdg_user_dirs(data):
    """Parses xdg-user-dirs and returns a dict of keys and paths.

    The paths depend on the content of os.environ while calling this function.
    See http://www.freedesktop.org/wiki/Software/xdg-user-dirs/

    Can't fail (but might return garbage).
    """
    paths = {}

    for line in data.splitlines():
        if line.startswith("#"):
            continue
        parts = line.split("=", 1)
        if len(parts) <= 1:
            continue
        key = parts[0]
        try:
            values = shlex.split(parts[1])
        except ValueError:
            continue
        if len(values) != 1:
            continue
        paths[key] = os.path.normpath(
            expandvars(bytes2fsn(values[0], "utf-8")))

    return paths


def xdg_get_user_dirs():
    """Returns a dict of xdg keys to paths. The paths don't have to exist."""
    config_home = xdg_get_config_home()
    try:
        with open(os.path.join(config_home, "user-dirs.dirs"), "rb") as h:
            return parse_xdg_user_dirs(h.read())
    except EnvironmentError:
        return {}


def get_temp_cover_file(data):
    """Returns a file object or None"""

    try:
        # pass fsnative so that mkstemp() uses unicode on Windows
        fn = tempfile.NamedTemporaryFile(prefix=fsnative(u"tmp"))
        fn.write(data)
        fn.flush()
        fn.seek(0, 0)
    except EnvironmentError:
        return
    else:
        return fn


def _strip_win32_incompat(string, BAD='\:*?;"<>|'):
    """Strip Win32-incompatible characters from a Windows or Unix path."""

    if os.name == "nt":
        BAD += "/"

    if not string:
        return string

    new = "".join(map(lambda s: (s in BAD and "_") or s, string))
    parts = new.split(os.sep)

    def fix_end(string):
        return re.sub(r'[\. ]$', "_", string)
    return os.sep.join(map(fix_end, parts))


def strip_win32_incompat_from_path(string):
    """Strip Win32-incompatible chars from a path, ignoring os.sep
    and the drive part"""

    drive, tail = os.path.splitdrive(string)
    tail = os.sep.join(map(_strip_win32_incompat, tail.split(os.sep)))
    return drive + tail


def _normalize_darwin_path(filename, canonicalise=False):

    if canonicalise:
        filename = os.path.realpath(filename)
    filename = os.path.normpath(filename)

    decoded = filename.decode("utf-8", "quodlibet-osx-path-decode")

    try:
        return NSString.fileSystemRepresentation(decoded)
    except ValueError:
        return filename


def _normalize_path(filename, canonicalise=False):
    """Normalize a path on Windows / Linux
    If `canonicalise` is True, dereference symlinks etc
    by calling `os.path.realpath`
    """
    if canonicalise:
        filename = os.path.realpath(filename)
    filename = os.path.normpath(filename)
    return os.path.normcase(filename)


if sys.platform == "darwin":

    def _osx_path_decode_error_handler(error):
        bytes_ = bytearray(error.object[error.start:error.end])
        return (u"".join(map("%%%X".__mod__, bytes_)), error.end)

    codecs.register_error(
        "quodlibet-osx-path-decode", _osx_path_decode_error_handler)

    normalize_path = _normalize_darwin_path
else:
    normalize_path = _normalize_path


def path_equal(p1, p2, canonicalise=False):
    return normalize_path(p1, canonicalise) == normalize_path(p2, canonicalise)


def limit_path(path, ellipsis=True):
    """Reduces the filename length of all filenames in the given path
    to the common maximum length for current platform.

    While the limits are depended on the file system and more restrictions
    may apply, this covers the common case.
    """

    assert isinstance(path, fsnative)

    main, ext = os.path.splitext(path)
    parts = main.split(sep)
    for i, p in enumerate(parts):
        # Limit each path section to 255 (bytes on linux, chars on win).
        # http://en.wikipedia.org/wiki/Comparison_of_file_systems#Limits
        limit = 255
        if i == len(parts) - 1:
            limit -= len(ext)

        if len(p) > limit:
            if ellipsis:
                p = p[:limit - 2] + fsnative(u"..")
            else:
                p = p[:limit]
        parts[i] = p

    return sep.join(parts) + ext


def get_home_dir():
    """Returns the root directory of the user, /home/user or C:\\Users\\user"""

    if os.name == "nt":
        return windows.get_profile_dir()
    else:
        return expanduser("~")


def uri_is_valid(uri):
    """Returns True if the passed in text is a valid URI (file, http, etc.)

    Returns:
        bool
    """

    if not isinstance(uri, bytes):
        uri = uri.encode("ascii")

    parsed = urlparse(uri)
    if not parsed.scheme or not len(parsed.scheme) > 1:
        return False
    elif not (parsed.netloc or parsed.path):
        return False
    else:
        return True
