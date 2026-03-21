# Copyright 2016 Christoph Reiter
#
# SPDX-License-Identifier: GPL-2.0-or-later

import re
import os

from ._fsnative import path2fsn, fsnative, is_win
from ._environ import environ


sep = path2fsn(os.sep)
pathsep = path2fsn(os.pathsep)
curdir = path2fsn(os.curdir)
pardir = path2fsn(os.pardir)
altsep = path2fsn(os.altsep) if os.altsep is not None else None
extsep = path2fsn(os.extsep)
devnull = path2fsn(os.devnull)
defpath = path2fsn(os.defpath)


def getcwd():
    """Like `os.getcwd` but returns a `fsnative` path

    Returns:
        `fsnative`
    """

    return os.getcwd()


def _get_userdir(user=None):
    """Returns the user dir or None"""

    if user is not None and not isinstance(user, fsnative):
        raise TypeError

    if is_win:
        if "USERPROFILE" in environ:
            path = environ["USERPROFILE"]
        elif "HOMEPATH" in environ and "HOMEDRIVE" in environ:
            path = os.path.join(environ["HOMEDRIVE"], environ["HOMEPATH"])
        else:
            return None

        path = os.path.normpath(path)

        if user is None:
            return path
        return os.path.join(os.path.dirname(path), user)
    import pwd

    if user is None:
        if "HOME" in environ:
            return environ["HOME"]
        try:
            return path2fsn(pwd.getpwuid(os.getuid()).pw_dir)
        except KeyError:
            return None
    else:
        try:
            return path2fsn(pwd.getpwnam(user).pw_dir)
        except KeyError:
            return None


def expanduser(path):
    """
    Args:
        path (pathlike): A path to expand
    Returns:
        `fsnative`

    Like :func:`python:os.path.expanduser` but supports unicode home
    directories under Windows + Python 2 and always returns a `fsnative`.
    """

    path = path2fsn(path)

    if path == "~":
        return _get_userdir()
    if path.startswith("~" + sep) or (
        altsep is not None and path.startswith("~" + altsep)
    ):
        userdir = _get_userdir()
        if userdir is None:
            return path
        return userdir + path[1:]
    if path.startswith("~"):
        sep_index = path.find(sep)
        if altsep is not None:
            alt_index = path.find(altsep)
            if alt_index != -1 and alt_index < sep_index:
                sep_index = alt_index

        if sep_index == -1:
            user = path[1:]
            rest = ""
        else:
            user = path[1:sep_index]
            rest = path[sep_index:]

        userdir = _get_userdir(user)
        if userdir is not None:
            return userdir + rest
        return path
    return path


def expandvars(path):
    """
    Args:
        path (pathlike): A path to expand
    Returns:
        `fsnative`

    Like :func:`python:os.path.expandvars` but supports unicode under Windows
    + Python 2 and always returns a `fsnative`.
    """

    path = path2fsn(path)

    def repl_func(match):
        return environ.get(match.group(1), match.group(0))

    path = re.compile(r"\$(\w+)", flags=re.UNICODE).sub(repl_func, path)
    if os.name == "nt":
        path = re.sub(r"%([^%]+)%", repl_func, path)
    return re.sub(r"\$\{([^\}]+)\}", repl_func, path)
