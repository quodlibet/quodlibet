# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import sys
import collections
import ctypes

if os.name == "nt":
    from win32com.shell import shellcon, shell
    import pywintypes
    import pythoncom


SHGFP_TYPE_CURRENT = 0
SHGFP_TYPE_DEFAULT = 1

CSIDL_FLAG_CREATE = 0x8000
CSIDL_FLAG_DONT_UNEXPAND = 0x2000


def _get_path(folder, default=False, create=False):
    """A path to an directory or None"""

    if default:
        flags = SHGFP_TYPE_DEFAULT
    else:
        flags = SHGFP_TYPE_CURRENT

    if create:
        folder |= CSIDL_FLAG_CREATE

    # we don't want env vars
    folder |= CSIDL_FLAG_DONT_UNEXPAND

    try:
        # returns either unicode or ascii str, depending on the env
        path = shell.SHGetFolderPath(0, folder, 0, flags)
    except pywintypes.com_error:
        return

    if not isinstance(path, unicode):
        path = path.decode("ascii")

    return path


def get_personal_dir(**kwargs):
    return _get_path(shellcon.CSIDL_PERSONAL, **kwargs)


def get_appdate_dir(**kwargs):
    return _get_path(shellcon.CSIDL_APPDATA, **kwargs)


def get_desktop_dir(**kwargs):
    return _get_path(shellcon.CSIDL_DESKTOP, **kwargs)


def get_music_dir(**kwargs):
    return _get_path(shellcon.CSIDL_MYMUSIC, **kwargs)


def get_profile_dir(**kwargs):
    return _get_path(shellcon.CSIDL_PROFILE, **kwargs)


def get_link_target(path):
    """Takes a path to a .lnk file and returns a path the .lnk file
    is targeting or None.
    """

    from quodlibet.util.path import fsnative

    link = pythoncom.CoCreateInstance(
        shell.CLSID_ShellLink, None,
        pythoncom.CLSCTX_INPROC_SERVER,
        shell.IID_IShellLink)

    try:
        link.QueryInterface(pythoncom.IID_IPersistFile).Load(path)
        # FIXME: this only supports the old ascii API..
        path = link.GetPath(0)[0]
        return path.decode("ascii")
    except pywintypes.com_error:
        pass


def get_links_dir():
    """Get the path to the Links directory (%USERPROFILE%\\Links) or None"""

    try:
        kfm = pythoncom.CoCreateInstance(shell.CLSID_KnownFolderManager, None,
            pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IKnownFolderManager)
    except pywintypes.com_error:
        # WinXP for example
        return

    try:
        libs_folder = kfm.GetFolder(shell.FOLDERID_Links)
        # returns unicode
        return libs_folder.GetPath()
    except pywintypes.com_error:
        pass


if os.name == "nt":
    SetEnvironmentVariableW = ctypes.windll.kernel32.SetEnvironmentVariableW
    SetEnvironmentVariableW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
    SetEnvironmentVariableW.restype = ctypes.c_bool

    GetEnvironmentStringsW = ctypes.windll.kernel32.GetEnvironmentStringsW
    GetEnvironmentStringsW.argtypes = []
    GetEnvironmentStringsW.restype = ctypes.c_void_p

    FreeEnvironmentStringsW = ctypes.windll.kernel32.FreeEnvironmentStringsW
    FreeEnvironmentStringsW.argtypes = [ctypes.c_void_p]
    FreeEnvironmentStringsW.restype = ctypes.c_bool


class WindowsEnvironError(Exception):
    pass


def _set_windows_env_var(key, value):
    """Set an env var.

    Can raise WindowsEnvironError
    """

    if not isinstance(key, unicode):
        raise TypeError

    if not isinstance(value, unicode):
        raise TypeError

    status = SetEnvironmentVariableW(key, value)
    if status == 0:
        raise WindowsEnvironError


def _del_windows_env_var(key):
    """Delete an env var.

    Can raise WindowsEnvironError
    """

    if not isinstance(key, unicode):
        raise TypeError

    status = SetEnvironmentVariableW(key, None)
    if status == 0:
        raise WindowsEnvironError


def _get_windows_environ():
    """Returns a unicode dict of the Windows environment.

    Can raise WindowsEnvironError
    """

    res = GetEnvironmentStringsW()
    if not res:
        raise WindowsEnvironError

    res = ctypes.cast(res, ctypes.POINTER(ctypes.c_wchar))

    done = []
    current = u""
    i = 0
    while 1:
        c = res[i]
        i += 1
        if c == u"\x00":
            if not current:
                break
            done.append(current)
            current = u""
            continue
        current += c

    dict_ = {}
    for entry in done:
        try:
            key, value = entry.split(u"=", 1)
        except ValueError:
            continue
        dict_[key] = value

    status = FreeEnvironmentStringsW(res)
    if status == 0:
        raise WindowsEnvironError

    return dict_


class WindowsEnviron(collections.MutableMapping):
    """os.environ that supports unicode on Windows.

    Keys can either be ascii bytes or unicode

    Like os.environ it will only contain the environment content present at
    load time. Changes will be synced with the real environment.
    """

    def __init__(self):
        try:
            env = _get_windows_environ()
        except WindowsEnvironError:
            env = {}
        self._env = env

    def __getitem__(self, key):
        if isinstance(key, bytes):
            key = key.decode("ascii")

        return self._env[key]

    def __setitem__(self, key, value):
        if isinstance(key, bytes):
            key = key.decode("ascii")

        try:
            _set_windows_env_var(key, value)
        except WindowsEnvironError:
            pass
        self._env[key] = value

    def __delitem__(self, key):
        if isinstance(key, bytes):
            key = key.decode("ascii")

        try:
            _del_windows_env_var(key)
        except WindowsEnvironError:
            pass
        del self._env[key]

    def __iter__(self):
        return iter(self._env)

    def __len__(self):
        return len(self._env)

    def __repr__(self):
        return repr(self._env)
