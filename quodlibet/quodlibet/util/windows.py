# -*- coding: utf-8 -*-
# Copyright 2013,2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from __future__ import absolute_import

import os
import sys
import collections
import ctypes

if os.name == "nt":
    from win32com.shell import shell
    import pywintypes
    import pythoncom
    from .winapi import SHGFPType, CSIDLFlag, CSIDL, GUID, \
        SHGetFolderPathW, SetEnvironmentVariableW, S_OK, \
        GetEnvironmentStringsW, FreeEnvironmentStringsW, \
        GetCommandLineW, CommandLineToArgvW, LocalFree, MAX_PATH, \
        KnownFolderFlag, FOLDERID, SHGetKnownFolderPath, CoTaskMemFree


def _get_path(folder, default=False, create=False):
    """A path to an directory or None.

    Takes a CSIDL instance as folder.
    """

    if default:
        flags = SHGFPType.DEFAULT
    else:
        flags = SHGFPType.CURRENT

    if create:
        folder |= CSIDLFlag.CREATE

    # we don't want env vars
    folder |= CSIDLFlag.DONT_UNEXPAND

    buffer_ = ctypes.create_unicode_buffer(MAX_PATH)
    try:
        result = SHGetFolderPathW(0, folder, 0, flags, buffer_)
    except WindowsError:
        return None
    if result != S_OK:
        return None
    return buffer_.value


def _get_known_path(folder, default=False, create=False):
    """A path to an directory or None

    Takes a FOLDERID instances as folder.
    """

    if default:
        flags = KnownFolderFlag.DEFAULT_PATH
    else:
        flags = 0

    if create:
        flags |= KnownFolderFlag.CREATE

    flags |= KnownFolderFlag.DONT_VERIFY

    ptr = ctypes.c_wchar_p()
    guid = GUID.from_uuid(folder)
    try:
        result = SHGetKnownFolderPath(
            ctypes.byref(guid), flags, None, ctypes.byref(ptr))
    except WindowsError:
        return None
    if result != S_OK:
        return None
    path = ptr.value
    CoTaskMemFree(ptr)
    return path


def get_personal_dir(**kwargs):
    r"""e.g. 'C:\Users\<user>\Documents'"""

    return _get_path(CSIDL.PERSONAL, **kwargs)


def get_appdate_dir(**kwargs):
    r"""e.g. 'C:\Users\<user>\AppDate\Roaming'"""

    return _get_path(CSIDL.APPDATA, **kwargs)


def get_desktop_dir(**kwargs):
    r"""e.g. 'C:\Users\<user>\Desktop'"""

    return _get_path(CSIDL.DESKTOP, **kwargs)


def get_music_dir(**kwargs):
    r"""e.g. 'C:\Users\<user>\Music'"""

    return _get_path(CSIDL.MYMUSIC, **kwargs)


def get_profile_dir(**kwargs):
    r"""e.g. 'C:\Users\<user>'"""

    return _get_path(CSIDL.PROFILE, **kwargs)


def get_links_dir(**kwargs):
    r"""e.g. 'C:\Users\<user>\Links'"""

    return _get_known_path(FOLDERID.LINKS, **kwargs)


def get_link_target(path):
    """Takes a path to a .lnk file and returns a path the .lnk file
    is targeting or None.
    """

    link = pythoncom.CoCreateInstance(
        shell.CLSID_ShellLink, None,
        pythoncom.CLSCTX_INPROC_SERVER,
        shell.IID_IShellLink)

    try:
        link.QueryInterface(pythoncom.IID_IPersistFile).Load(path)
        # FIXME: this only supports the old non-unicode API..
        path = link.GetPath(0)[0]
        return path.decode("latin-1")
    except pywintypes.com_error:
        pass


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


def get_win32_unicode_argv():
    """Returns a unicode version of sys.argv"""

    argc = ctypes.c_int()
    argv = CommandLineToArgvW(GetCommandLineW(), ctypes.byref(argc))
    if not argv:
        return []

    res = argv[max(0, argc.value - len(sys.argv)):argc.value]

    LocalFree(argv)
    return res
