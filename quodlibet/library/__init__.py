# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Various library classes.

Libraries are (roughly) dicts of items, and in the case of Quod Libet,
these items are songs. Libraries are in charge of alerting the rest of
the program when songs have been added, changed, or removed. They can
also be queried in various ways.
"""

import time

from quodlibet import print_d, print_w, config

from quodlibet.library.song import SongLibrary, SongFileLibrary
from quodlibet.library.librarians import SongLibrarian
from quodlibet.util.library import get_scan_dirs
from quodlibet.util.path import mtime


def init(cache_fn=None):
    """Set up the library and return the main one.

    Return a main library, and set a librarian for
    all future SongLibraries.
    """

    SongFileLibrary.librarian = SongLibrary.librarian = SongLibrarian()
    watch = config.getboolean("library", "watch")
    library = SongFileLibrary("main", watch_dirs=get_scan_dirs() if watch else [])
    if cache_fn:
        library.load(cache_fn)
    return library


def save(save_period=None):
    """Save all registered libraries that have a filename and are marked dirty.

    If `save_period` (seconds) is given the library will only be saved if
    it hasn't been in the last `save_period` seconds.
    """

    print_d("Saving all libraries...")

    librarian = SongFileLibrary.librarian
    for lib in librarian.libraries.values():
        filename = lib.filename
        if not filename or not lib.dirty:
            continue

        if not save_period or abs(time.time() - mtime(filename)) > save_period:
            lib.save()


def destroy() -> None:
    """Destroy all registered libraries """

    print_d("Destroying all libraries...")

    librarian = SongFileLibrary.librarian
    if librarian:
        for lib in list(librarian.libraries.values()):
            try:
                lib.destroy()
            except Exception as e:
                print_w(f"Couldn't destroy {lib} ({e!r})")
        librarian.destroy()
