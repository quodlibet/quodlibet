# -*- coding: utf-8 -*-
# Copyright 2011 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import sys
import errno
import urllib
import time

from os.path import join, islink, abspath, dirname
from os.path import isdir, basename, exists, splitext

from quodlibet.util import xdg_get_data_home, find_mount_point

class TrashError(EnvironmentError):
    pass

def is_sticky(path):
    return bool(os.stat(path).st_mode & (1<9))

def get_fd_trash_dir(path):
    """Returns the right trash directory for the given path."""

    path = abspath(path)
    mount = find_mount_point(path)
    xdg_data_home = xdg_get_data_home()
    xdg_mount = find_mount_point(xdg_data_home)
    if mount == xdg_mount:
        trash_home = join(xdg_data_home, "Trash")
        return trash_home
    else:
        root = join(mount, ".Trash")
        uid = str(os.getuid())
        if isdir(root) and not islink(root) and is_sticky(root):
            root = join(root, uid)
        else:
            root = join(mount, ".Trash-" + uid)
        return root

def trash_free_desktop(path):
    """Partial implementation of
    http://www.freedesktop.org/wiki/Specifications/trash-spec

    No copy fallback, either it can be moved on the same FS or it failes.
    Also doesn't work for files in the trash directory.
    """

    path = abspath(path)

    if not exists(path):
        raise TrashError("Path %s does not exist." % path)

    trash_dir = abspath(get_fd_trash_dir(path))

    # to make things easier
    if path.startswith(join(trash_dir, "")) or path == trash_dir:
        raise TrashError("Can't move files to the trash from within the"
            "trash directory.")

    files = join(trash_dir, "files")
    info = join(trash_dir, "info")

    for d in (files, info):
        if not isdir(d): os.makedirs(d, 0700)

    info_ext = ".trashinfo"
    name = basename(path)
    flags = os.O_EXCL | os.O_CREAT | os.O_WRONLY
    mode = 0644
    try:
        info_path = join(info, name + info_ext)
        info_fd = os.open(info_path, flags, mode)
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise
        i = 2
        while 1:
            head, tail = splitext(name)
            temp_name = "%s.%d%s" % (head, i, tail)
            info_path = join(info, temp_name + info_ext)
            try:
                info_fd = os.open(info_path, flags, mode)
            except OSError, e:
                if e.errno != errno.EEXIST:
                    raise
                i += 1
                continue
            name = temp_name
            break

    parent = dirname(trash_dir)
    if path.startswith(join(parent, "")):
        norm_path = path[len(join(parent, "")):]
    else:
        norm_path = path

    del_date = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())

    data = "[Trash Info]\n"
    data += "Path=%s\n" % urllib.pathname2url(norm_path)
    data += "DeletionDate=%s\n" % del_date
    os.write(info_fd, data)
    os.close(info_fd)

    try:
        # We only move to the same file system.. so this is ok.
        os.rename(path, join(files, name))
    except OSError:
        # In case something failes, remove the info file and raise again
        os.unlink(info_path)
        raise

def can_trash():
    """If the current platform supports moving files into a trash can."""
    return (os.name == "posix" and sys.platform != "darwin")

def trash(path):
    if os.name == "posix" and sys.platform != "darwin":
        trash_free_desktop(path)
    else:
        raise NotImplementedError
