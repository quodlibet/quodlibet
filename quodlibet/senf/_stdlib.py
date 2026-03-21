# Copyright 2016 Christoph Reiter
#
# SPDX-License-Identifier: GPL-2.0-or-later

import re
import os

from ._fsnative import path2fsn, fsnative, is_win


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
        if "USERPROFILE" in os.environ:
            path = os.environ["USERPROFILE"]
        elif "HOMEPATH" in os.environ and "HOMEDRIVE" in os.environ:
            path = os.path.join(os.environ["HOMEDRIVE"], os.environ["HOMEPATH"])
        else:
            return None

        path = os.path.normpath(path)

        if user is None:
            return path
        return os.path.join(os.path.dirname(path), user)
    import pwd

    if user is None:
        if "HOME" in os.environ:
            return os.environ["HOME"]
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
    if path.startswith("~" + os.sep) or (
        os.altsep is not None and path.startswith("~" + os.altsep)
    ):
        userdir = _get_userdir()
        if userdir is None:
            return path
        return userdir + path[1:]
    if path.startswith("~"):
        sep_index = path.find(os.sep)
        if os.altsep is not None:
            alt_index = path.find(os.altsep)
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
        return os.environ.get(match.group(1), match.group(0))

    path = re.compile(r"\$(\w+)", flags=re.UNICODE).sub(repl_func, path)
    if os.name == "nt":
        path = re.sub(r"%([^%]+)%", repl_func, path)
    return re.sub(r"\$\{([^\}]+)\}", repl_func, path)
