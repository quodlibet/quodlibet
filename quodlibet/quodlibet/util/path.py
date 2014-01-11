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
import urllib
from quodlibet.const import FSCODING as fscoding
from quodlibet.util.string import decode, encode
from quodlibet import windows

"""
Path related functions like open, os.listdir have different behavior on win32

- Passing a string calls the old non unicode win API.
  In case of listdir this leads to "?" for >1byte chars and to
  1 byte chars encoded using the fs encoding. -> DO NOT USE!

- Passing a unicode object internally calls the windows unicode functions.
  This will mostly lead to proper unicode paths (except expanduser).

  And that's why QL is using unicode paths on win and encoded paths
  everywhere else.
"""


def mkdir(dir_, *args):
    """Make a directory, including all its parent directories. This does not
    raise an exception if the directory already exists (and is a
    directory)."""

    try:
        os.makedirs(dir_, *args)
    except OSError as e:
        if e.errno != errno.EEXIST or not os.path.isdir(dir_):
            raise


def fsdecode(s, note=True):
    """Decoding a string according to the filesystem encoding.
    note specifies whether a note should be appended if decoding failed."""
    if isinstance(s, unicode):
        return s
    elif note:
        return decode(s, fscoding)
    else:
        return s.decode(fscoding, 'replace')


def fsencode(s, note=False):
    """Encode a string according to the filesystem encoding.
    note specifies whether a note should be appended if encoding failed."""
    if isinstance(s, str):
        return s
    elif note:
        return encode(s, fscoding)
    else:
        return s.encode(fscoding, 'replace')


if sys.platform == "win32":
    fsnative = fsdecode  # Decode a filename on windows
    is_fsnative = lambda s: isinstance(s, unicode)
else:
    fsnative = fsencode  # Encode it on other platforms
    is_fsnative = lambda s: isinstance(s, str)


def iscommand(s):
    """True if an executable file 's' exists in the user's path, or is a
    fully-qualified existing executable file."""

    if s == "" or os.path.sep in s:
        return os.path.isfile(s) and os.access(s, os.X_OK)
    else:
        s = s.split()[0]
        for p in os.defpath.split(os.path.pathsep):
            p2 = os.path.join(p, s)
            if os.path.isfile(p2) and os.access(p2, os.X_OK):
                return True
        else:
            return False


def listdir(path, hidden=False):
    """List files in a directory, sorted, fully-qualified.

    If hidden is false, Unix-style hidden files are not returned.
    """
    path = fsnative(path)
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
    """Escape a string in a manner suitable for a filename."""
    if isinstance(s, unicode):
        s = s.encode("utf-8")
    return urllib.quote(s, safe="").decode("utf-8")


def unescape_filename(s):
    """Unescape a string in a manner suitable for a filename."""
    if isinstance(s, unicode):
        s = s.encode("utf-8")
    return urllib.unquote(s).decode("utf-8")


def expanduser(filename):
    """needed because expanduser does not return wide character paths
    on windows even if a unicode path gets passed.
    """

    if os.name == "nt":
        profile = windows.get_profile_dir() or u""
        if filename == "~":
            return profile
        if filename.startswith(u"~" + os.path.sep):
            return os.path.join(profile, filename[2:])
    return os.path.expanduser(filename)


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


def pathname2url_win32(path):
    # stdlib version raises IOError for more than one ':' which can appear
    # using a virtual box shared folder and it inserts /// at the beginning
    # but it should be /.

    # windows paths should be unicode
    if isinstance(path, unicode):
        path = path.encode("utf-8")

    quote = urllib.quote
    if path[1:2] != ":" or path[:1] == "\\":
        if path[:2] == "\\\\":
            path = path[2:]
        return quote("/".join(path.split("\\")))
    drive, remain = path.split(":", 1)
    return "/%s:%s" % (quote(drive), quote("/".join(remain.split("\\"))))

if os.name == "nt":
    pathname2url = pathname2url_win32
else:
    pathname2url = urllib.pathname2url


def xdg_get_system_data_dirs():
    """http://standards.freedesktop.org/basedir-spec/latest/"""

    if os.name == "nt":
        from gi.repository import GLib
        return map(fsnative, GLib.get_system_data_dirs())

    data_dirs = os.getenv("XDG_DATA_DIRS")
    if data_dirs:
        return map(os.path.abspath, data_dirs.split(":"))
    else:
        return ("/usr/local/share/", "/usr/share/")


def xdg_get_cache_home():

    if os.name == "nt":
        from gi.repository import GLib
        return fsnative(GLib.get_user_cache_dir())

    data_home = os.getenv("XDG_CACHE_HOME")
    if data_home:
        return os.path.abspath(data_home)
    else:
        return os.path.join(os.path.expanduser("~"), ".cache")


def xdg_get_data_home():
    if os.name == "nt":
        from gi.repository import GLib
        return fsnative(GLib.get_user_data_dir())

    data_home = os.getenv("XDG_DATA_HOME")
    if data_home:
        return os.path.abspath(data_home)
    else:
        return os.path.join(os.path.expanduser("~"), ".local", "share")


def get_temp_cover_file(data):
    try:
        fn = tempfile.NamedTemporaryFile()
        fn.write(data)
        fn.flush()
        fn.seek(0, 0)
    except EnvironmentError:
        return
    else:
        return fn


def strip_win32_incompat(string, BAD='\:*?;"<>|'):
    """Strip Win32-incompatible characters from a Windows or Unix path."""

    if os.name == "nt":
        BAD += "/"

    new = "".join(map(lambda s: (s in BAD and "_") or s, string))
    parts = new.split(os.sep)

    def fix_end(string):
        return re.sub(r'[\. ]$', "_", string)
    return os.sep.join(map(fix_end, parts))


def strip_win32_incompat_from_path(string):
    """Strip Win32-incompatible chars from a path, ignoring os.sep
    and the drive part"""
    drive, tail = os.path.splitdrive(string)
    tail = os.sep.join(map(strip_win32_incompat, tail.split(os.sep)))
    return drive + tail


def _normalize_darwin_path(filename, strict=False, _cache={}, _statcache={}):
    """Get a normalized version of the path by calling listdir
    and comparing the inodes with our file.

    - This should also work on linux, but returns the same as os.path.normpath.
    - Any errors get ignored and lead to an un-normalized version.
    - Supports relative and absolute paths (and returns the same).
    """

    if filename in (".", "..", "/", ""):
        return filename

    filename = os.path.normpath(filename)

    def _stat(p):
        assert p.startswith("/")

        if len(_statcache) > 100:
            _statcache.clear()
        if p not in _statcache:
            _statcache[p] = os.lstat(p)
        return _statcache[p]

    abspath = os.path.abspath(filename)
    key = (abspath, filename)
    if key in _cache:
        return _cache[key]
    parent = os.path.dirname(abspath)

    try:
        s1 = _stat(abspath)
        for entry in os.listdir(parent):
            entry_path = os.path.join(parent, entry)
            if not os.path.samestat(s1, _stat(entry_path)):
                continue
            dirname = os.path.dirname(filename)
            norm_dirname = _normalize_darwin_path(dirname)
            filename = os.path.join(norm_dirname, entry)
            break
    except EnvironmentError:
        if strict:
            raise

    if len(_cache) > 30:
        _cache.clear()

    _cache[key] = filename
    return filename


def _normalize_path(filename):
    """Normalize a path on Windows / Linux"""

    filename = os.path.normpath(filename)
    return os.path.normcase(filename)


if sys.platform == "darwin":
    normalize_path = _normalize_darwin_path
else:
    normalize_path = _normalize_path
