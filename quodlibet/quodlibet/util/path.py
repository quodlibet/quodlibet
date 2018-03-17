# -*- coding: utf-8 -*-
# Copyright 2004-2009 Joe Wreschnig, Michael Urman, Steven Robertson
#           2011-2013 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import io
import re
import sys
import errno
import codecs
import shlex

from senf import fsnative, bytes2fsn, fsn2bytes, expanduser, sep, expandvars, \
    fsn2text, path2fsn

from quodlibet.compat import PY2, urlparse, text_type, quote, unquote, PY3
from . import windows
from .environment import is_windows
from .misc import environ, NamedTemporaryFile

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

    Args:
        s (text_type)
    Returns:
        fsnative
    """

    s = text_type(s)
    s = quote(s.encode("utf-8"), safe=b"")
    if isinstance(s, text_type):
        s = s.encode("ascii")
    return bytes2fsn(s, "utf-8")


def unescape_filename(s):
    """Unescape a string in a manner suitable for a filename.

    Args:
        filename (fsnative)
    Returns:
        text_type
    """

    assert isinstance(s, fsnative)

    return fsn2text(unquote(s))


def unexpand(filename):
    """Replace the user's home directory with ~ or %USERPROFILE%, if it
    appears at the start of the path name.

    Args:
        filename (fsnative): The file path
    Returns:
        fsnative: The path with the home directory replaced
    """

    sub = (os.name == "nt" and fsnative(u"%USERPROFILE%")) or fsnative(u"~")
    home = expanduser("~")
    if filename == home:
        return sub
    elif filename.startswith(home + os.path.sep):
        filename = filename.replace(home, sub, 1)
    return filename


if PY3 and is_windows():
    def ismount(path):
        # this can raise on py3+win, but we don't care
        try:
            return os.path.ismount(path)
        except OSError:
            return False
else:
    ismount = os.path.ismount


def find_mount_point(path):
    while not ismount(path):
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
        return list(map(os.path.abspath, data_dirs.split(":")))
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

    The paths depend on the content of environ while calling this function.
    See http://www.freedesktop.org/wiki/Software/xdg-user-dirs/

    Args:
        data (bytes)

    Can't fail (but might return garbage).
    """

    assert isinstance(data, bytes)

    paths = {}
    for line in data.splitlines():
        if line.startswith(b"#"):
            continue
        parts = line.split(b"=", 1)
        if len(parts) <= 1:
            continue
        key = parts[0]
        try:
            values = shlex.split(bytes2fsn(parts[1], "utf-8"))
        except ValueError:
            continue
        if len(values) != 1:
            continue
        paths[key] = os.path.normpath(expandvars(values[0]))

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
        fn = NamedTemporaryFile(prefix=fsnative(u"tmp"))
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

    filename = path2fsn(filename)

    if canonicalise:
        filename = os.path.realpath(filename)
    filename = os.path.normpath(filename)

    data = fsn2bytes(filename, "utf-8")
    decoded = data.decode("utf-8", "quodlibet-osx-path-decode")

    try:
        return bytes2fsn(
            NSString.fileSystemRepresentation(decoded), "utf-8")
    except ValueError:
        return filename


def _normalize_path(filename, canonicalise=False):
    """Normalize a path on Windows / Linux
    If `canonicalise` is True, dereference symlinks etc
    by calling `os.path.realpath`
    """
    filename = path2fsn(filename)
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


def ishidden(path):
    """Returns if a directory/ file is considered hidden by the platform.

    Hidden meaning the user should normally not be exposed to those files when
    opening the parent directory in the default file manager using the default
    settings.

    Does not check if any of the parents are hidden.
    In case the file/dir does not exist the result is implementation defined.

    Args:
        path (fsnative)
    Returns:
        bool
    """

    # TODO: win/osx
    return os.path.basename(path).startswith(".")


def uri_is_valid(uri):
    """Returns True if the passed in text is a valid URI (file, http, etc.)

    Args:
        uri(text or bytes)
    Returns:
        bool
    """

    try:
        if isinstance(uri, bytes):
            uri.decode("ascii")
        elif not isinstance(uri, bytes):
            uri = uri.encode("ascii")
    except ValueError:
        return False

    parsed = urlparse(uri)
    if not parsed.scheme or not len(parsed.scheme) > 1:
        return False
    elif not (parsed.netloc or parsed.path):
        return False
    else:
        return True


class RootPathFile:
    """Simple container used for discerning a pathfile's 'root' directory
    and 'end' part. The variable depth of a pathfile's 'end' part renders
    os.path built-ins (basename etc.) useless for this purpose"""

    _root = ''  # 'root' of full file path
    _pathfile = ''  # full file path

    def __init__(self, root, pathfile):
        self._root = root
        self._pathfile = pathfile

    @property
    def root(self):
        return self._root

    @property
    def end(self):
        return self._pathfile[len(self._root) + len(os.sep):]

    @property
    def pathfile(self):
        return self._pathfile

    @property
    def end_escaped(self):
        escaped = [escape_filename(part)
                    for part in self.end.split(os.path.sep)]
        return os.path.sep.join(escaped)

    @property
    def pathfile_escaped(self):
        return os.path.sep.join([self.root, self.end_escaped])

    @property
    def valid(self):
        valid = True
        if os.path.exists(self.pathfile):
            return valid
        else:
            try:
                with io.open(self.pathfile, "w", encoding='utf-8') as f:
                    f.close()  # do nothing
            except OSError:
                valid = False
            if os.path.exists(self.pathfile):
                os.remove(self.pathfile)
            return valid
