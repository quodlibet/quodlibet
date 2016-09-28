# -*- coding: utf-8 -*-
# Copyright 2004-2013 Joe Wreschnig, Michael Urman, Iñigo Serna,
#     Christoph Reiter, Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import re
import sys

from senf import fsn2bytes, bytes2fsn, fsnative

from quodlibet import _
from quodlibet import app
from quodlibet import config
from quodlibet.qltk.notif import Task
from quodlibet.util.dprint import print_d
from quodlibet.util import copool

from quodlibet.query import Query
from quodlibet.qltk.songlist import SongList
from quodlibet.util.string import split_escape, join_escape


def background_filter():
    bg = config.gettext("browsers", "background")
    if not bg:
        return
    try:
        return Query(bg, SongList.star).search
    except Query.error:
        pass


def split_scan_dirs(s):
    """Split the value of the "scan" setting, accounting for drive letters on
    win32."""
    if sys.platform == "win32":
        return filter(None, re.findall(r"[a-zA-Z]:[\\/][^:]*", s))
    else:
        # See Issue 1413 - allow escaped colons
        return filter(None, split_escape(s, ":"))


def get_scan_dirs():
    dirs = split_scan_dirs(config.get("settings", "scan"))
    return [bytes2fsn(d, "utf-8") for d in dirs if d]


def set_scan_dirs(dirs):
    if sys.platform == "win32":
        joined = fsnative(u":").join(dirs)
    else:
        joined = join_escape(dirs, fsnative(u":"))
    config.set("settings", "scan", fsn2bytes(joined, "utf-8"))


def scan_library(library, force):
    """Start the global library re-scan

    If `force` is True, reload all existing valid items.
    """

    paths = get_scan_dirs()
    exclude = split_scan_dirs(config.get("library", "exclude"))
    exclude = [bytes2fsn(e, "utf-8") for e in exclude]
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
