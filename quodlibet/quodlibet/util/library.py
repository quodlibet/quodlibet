# -*- coding: utf-8 -*-
# Copyright 2004-2017 Joe Wreschnig, Michael Urman, Iñigo Serna,
#     Christoph Reiter, Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import re

from senf import fsn2bytes, bytes2fsn, fsnative, expanduser

from quodlibet import _
from quodlibet import app
from quodlibet import config
from quodlibet.qltk.notif import Task
from quodlibet.util.dprint import print_d
from quodlibet.util import copool, is_windows

from quodlibet.query import Query
from quodlibet.qltk.songlist import SongList
from quodlibet.util.string import split_escape, join_escape


def background_filter():
    """Returns a filter function for AudioFile or None if nothing should be
    filtered.

    The filter is meant to be used globally to hide songs from the main
    library.

    Returns:
        function or None
    """

    bg = config.gettext("browsers", "background")
    if not bg:
        return
    try:
        query = Query(bg, SongList.star)
        if query.is_parsable:
            return query.search
    except Query.error:
        pass


def split_scan_dirs(joined_paths):
    """Returns a list of paths

    Args:
        joined_paths (fsnative)
    Return:
        list
    """

    assert isinstance(joined_paths, fsnative)

    if is_windows():
        # we used to separate this config with ":", so this is tricky
        return list(
            filter(None, re.findall(r"[a-zA-Z]:[\\/][^:]*", joined_paths)))
    else:
        return list(filter(None, split_escape(joined_paths, ":")))


def get_scan_dirs():
    """Returns a list of paths which should be scanned

    Returns:
        list
    """

    joined_paths = bytes2fsn(config.getbytes("settings", "scan"), "utf-8")
    return [expanduser(p) for p in split_scan_dirs(joined_paths)]


def set_scan_dirs(dirs):
    """Saves a list of fs paths which should be scanned

    Args:
        list
    """

    assert all(isinstance(d, fsnative) for d in dirs)

    if is_windows():
        joined = fsnative(u":").join(dirs)
    else:
        joined = join_escape(dirs, fsnative(u":"))
    config.setbytes("settings", "scan", fsn2bytes(joined, "utf-8"))


def get_exclude_dirs():
    """Returns a list of paths which should be ignored during scanning

    Returns:
        list
    """

    paths = split_scan_dirs(
        bytes2fsn(config.getbytes("library", "exclude"), "utf-8"))
    return [expanduser(p) for p in paths]


def scan_library(library, force):
    """Start the global library re-scan

    Args:
        library (Library)
        force (bool): if True, reload all existing valid items
    """

    paths = get_scan_dirs()
    exclude = get_exclude_dirs()
    copool.add(library.rebuild, paths, force, exclude,
               cofuncid="library", funcid="library")


def emit_signal(songs, signal="changed", block_size=50, name=None,
                cofuncid=None):
    """
    A generator that signals `signal` on the library
    in blocks of `block_size`. Useful for copools.
    """
    i = 0
    with Task(_("Library"), name or signal) as task:
        if cofuncid:
            task.copool(cofuncid)
        total = len(songs)
        while i < total:
            more = songs[i:i + block_size]
            if not more:
                return
            if 0 == ((i / block_size) % 10):
                print_d("Signalling '%s' (%d/%d songs)"
                        % (signal, i, total))
            task.update(float(i) / total)
            app.library.emit(signal, more)
            i += block_size
            yield
