# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import sys

if os.name == "nt":
    from win32com.shell import shellcon, shell
    import win32profile
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


def get_environ():
    """Like os.environ, but with unicode support"""

    return win32profile.GetEnvironmentStrings()


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
        # Not sure what encoding this returns
        return fsnative(link.GetPath(0)[0])
    except pywintypes.com_error:
        pass


def get_links_dir():
    """Get the path to the Links directory (%USERPROFILE%\\Links) or None"""

    kfm = pythoncom.CoCreateInstance(shell.CLSID_KnownFolderManager, None,
        pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IKnownFolderManager)

    try:
        libs_folder = kfm.GetFolder(shell.FOLDERID_Links)
        return libs_folder.GetPath()
    except pywintypes.com_error:
        pass
