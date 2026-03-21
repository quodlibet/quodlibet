# Copyright 2016 Christoph Reiter
#
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import ctypes
from collections import abc

from ._fsnative import path2fsn, is_win, fsnative
from . import _winapi as winapi


def get_windows_env_var(key):
    """Get an env var.

    Raises:
        WindowsError
    """

    if not isinstance(key, str):
        raise TypeError("%r not of type %r" % (key, str))

    buf = ctypes.create_unicode_buffer(32767)

    stored = winapi.GetEnvironmentVariableW(key, buf, 32767)
    if stored == 0:
        raise ctypes.WinError()
    return buf[:stored]


def set_windows_env_var(key, value):
    """Set an env var.

    Raises:
        WindowsError
    """

    if not isinstance(key, str):
        raise TypeError("%r not of type %r" % (key, str))

    if not isinstance(value, str):
        raise TypeError("%r not of type %r" % (value, str))

    status = winapi.SetEnvironmentVariableW(key, value)
    if status == 0:
        raise ctypes.WinError()


def del_windows_env_var(key):
    """Delete an env var.

    Raises:
        WindowsError
    """

    if not isinstance(key, str):
        raise TypeError("%r not of type %r" % (key, str))

    status = winapi.SetEnvironmentVariableW(key, None)
    if status == 0:
        raise ctypes.WinError()


def read_windows_environ():
    """Returns a unicode dict of the Windows environment.

    Raises:
        WindowsEnvironError
    """

    res = winapi.GetEnvironmentStringsW()
    if not res:
        raise ctypes.WinError()

    res = ctypes.cast(res, ctypes.POINTER(ctypes.c_wchar))

    done = []
    current = ""
    i = 0
    while 1:
        c = res[i]
        i += 1
        if c == "\x00":
            if not current:
                break
            done.append(current)
            current = ""
            continue
        current += c

    dict_ = {}
    for entry in done:
        try:
            key, value = entry.split("=", 1)
        except ValueError:
            continue
        key = _norm_key(key)
        dict_[key] = value

    status = winapi.FreeEnvironmentStringsW(res)
    if status == 0:
        raise ctypes.WinError()

    return dict_


def _norm_key(key):
    assert isinstance(key, fsnative)
    if is_win:
        key = key.upper()
    return key


class Environ(abc.MutableMapping):
    """Dict[`fsnative`, `fsnative`]: Like `os.environ` but contains unicode
    keys and values under Windows + Python 2.

    Any changes made will be forwarded to `os.environ`.
    """

    def __init__(self):
        self._env = os.environ

    def __getitem__(self, key):
        key = _norm_key(path2fsn(key))
        return self._env[key]

    def __setitem__(self, key, value):
        key = _norm_key(path2fsn(key))
        value = path2fsn(value)

        try:
            self._env[key] = value
        except OSError:
            raise ValueError

    def __delitem__(self, key):
        key = _norm_key(path2fsn(key))

        del self._env[key]

    def __iter__(self):
        return iter(self._env)

    def __len__(self):
        return len(self._env)

    def __repr__(self):
        return repr(self._env)

    def copy(self):
        return self._env.copy()


environ = Environ()


def getenv(key, value=None):
    """Like `os.getenv` but returns unicode under Windows + Python 2

    Args:
        key (pathlike): The env var to get
        value (object): The value to return if the env var does not exist
    Returns:
        `fsnative` or `object`:
            The env var or the passed value if it doesn't exist
    """

    key = path2fsn(key)
    return os.getenv(key, value)


def unsetenv(key):
    """Like `os.unsetenv` but takes unicode under Windows + Python 2

    Args:
        key (pathlike): The env var to unset
    """

    key = path2fsn(key)
    if is_win:
        # python 3 has no unsetenv under Windows -> use our ctypes one as well
        try:
            del_windows_env_var(key)
        except OSError:
            pass
    else:
        os.unsetenv(key)


def putenv(key, value):
    """Like `os.putenv` but takes unicode under Windows + Python 2

    Args:
        key (pathlike): The env var to get
        value (pathlike): The value to set
    Raises:
        ValueError
    """

    key = path2fsn(key)
    value = path2fsn(value)

    try:
        os.putenv(key, value)
    except OSError:
        # win + py3 raise here for invalid keys which is probably a bug.
        # ValueError seems better
        raise ValueError
