# Copyright 2013,2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


import sys
import os
import ctypes


if sys.platform == "win32":
    from . import winapi
    from .winapi import SHGFPType, CSIDLFlag, CSIDL, GUID, \
        SHGetFolderPathW, S_OK, MAX_PATH, \
        KnownFolderFlag, FOLDERID, SHGetKnownFolderPath, CoTaskMemFree, \
        CoInitialize, IShellLinkW, CoCreateInstance, CLSID_ShellLink, \
        CLSCTX_INPROC_SERVER, IPersistFile


def open_folder_and_select_items(folder, items=None):
    """Shows a directory and optional files or subdirectories in the
    file manager (explorer.exe).

    If both folder and items is given the file manager will
    display the content of `folder` and highlight all `items`.

    If only a directory is given then the content of the parent directory is
    shown and the `folder` highlighted.

    Might raise WindowsError in case something fails (any of the
    files not existing etc.)
    """

    if items is None:
        items = []

    assert isinstance(folder, str)
    for item in items:
        assert isinstance(item, str)
        assert not os.path.split(item)[0]

    desktop = winapi.IShellFolder()
    parent = winapi.IShellFolder()
    parent_id = winapi.PIDLIST_ABSOLUTE()
    child_ids = (winapi.PIDLIST_RELATIVE * len(items))()

    try:
        winapi.CoInitialize(None)

        winapi.SHParseDisplayName(
            folder, None, ctypes.byref(parent_id), 0, None)

        winapi.SHGetDesktopFolder(ctypes.byref(desktop))

        desktop.BindToObject(
            parent_id, None, winapi.IShellFolder.IID, ctypes.byref(parent))

        for i, item in enumerate(items):
            attrs = winapi.ULONG(0)
            parent.ParseDisplayName(
                None, None, item, None,
                ctypes.byref(child_ids[i]), ctypes.byref(attrs))

        winapi.SHOpenFolderAndSelectItems(
            parent_id, len(child_ids),
            winapi.PCUITEMID_CHILD_ARRAY(child_ids), 0)
    finally:
        for child_id in child_ids:
            if child_id:
                winapi.CoTaskMemFree(child_id)
        if parent_id:
            winapi.ILFree(parent_id)
        if parent:
            parent.Release()
        if desktop:
            desktop.Release()


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
    except OSError:
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
    guid = GUID(folder)
    try:
        result = SHGetKnownFolderPath(
            ctypes.byref(guid), flags, None, ctypes.byref(ptr))
    except OSError:
        return None
    if result != S_OK:
        return None
    path = ptr.value
    CoTaskMemFree(ptr)
    return path


def get_personal_dir(**kwargs):
    r"""e.g. 'C:\Users\<user>\Documents'"""

    return _get_path(CSIDL.PERSONAL, **kwargs)


def get_appdata_dir(**kwargs):
    r"""e.g. 'C:\Users\<user>\AppData\Roaming'"""

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
    is targeting.

    Might raise WindowsError in case something fails.
    """

    assert isinstance(path, str)

    CoInitialize(None)

    pShellLinkW = IShellLinkW()
    CoCreateInstance(
        ctypes.byref(CLSID_ShellLink), None, CLSCTX_INPROC_SERVER,
        ctypes.byref(IShellLinkW.IID), ctypes.byref(pShellLinkW))
    try:
        pPersistFile = IPersistFile()
        pShellLinkW.QueryInterface(ctypes.byref(IPersistFile.IID),
                                   ctypes.byref(pPersistFile))
        try:
            buffer_ = ctypes.create_unicode_buffer(path, MAX_PATH)
            pPersistFile.Load(buffer_, 0)
        finally:
            pPersistFile.Release()
        pShellLinkW.GetPath(buffer_, MAX_PATH, None, 0)
    finally:
        pShellLinkW.Release()

    return ctypes.wstring_at(buffer_)
