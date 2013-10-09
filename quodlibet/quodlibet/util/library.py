# -*- coding: utf-8 -*-
# Copyright 2004-2013 Joe Wreschnig, Michael Urman, Iñigo Serna,
#     Christoph Reiter, Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet import app
from quodlibet import config
from quodlibet import util
from quodlibet.qltk.notif import Task
from quodlibet.util.dprint import print_d
from quodlibet.util import copool

from quodlibet.parse import Query
from quodlibet.qltk.songlist import SongList


def background_filter():
    bg = config.get("browsers", "background").decode('utf-8')
    if not bg:
        return
    try:
        return Query(bg, SongList.star).search
    except Query.error:
        pass


def get_scan_dirs():
    dirs = util.split_scan_dirs(config.get("settings", "scan"))
    return [util.fsnative(d) for d in dirs if d]


def set_scan_dirs(dirs):
    config.set("settings", "scan", util.fsencode(":".join(dirs)))


def scan_library(library, force):
    """Start the global library re-scan

    If `force` is True, reload all existing valid items.
    """

    paths = util.split_scan_dirs(config.get("settings", "scan"))
    exclude = config.get("library", "exclude").split(":")
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
