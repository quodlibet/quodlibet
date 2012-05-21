# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

"""Various library classes.

Libraries are (roughly) dicts of items, and in the case of Quod Libet,
these items are songs. Libraries are in charge of alerting the rest of
the program when songs have been added, changed, or removed. They can
also be queried in various ways.
"""

import time
import threading

from quodlibet import util
import quodlibet.formats as formats

from quodlibet.library.songs import SongFileLibrary, SongLibrary, SongLibrarian

librarian = library = None

def init(cache_fn=None):
    """Set up the library and return the main one.

    Create the 'global' main library, and also a librarian for
    all future SongLibraries.
    """
    global library, librarian
    s = ", ".join(formats.modules)
    print_d("Supported formats: %s" % s)
    SongFileLibrary.librarian = SongLibrary.librarian = SongLibrarian()
    library = SongFileLibrary("main")
    librarian = library.librarian
    if cache_fn:
        library.load(cache_fn, skip=formats.supported)
    return library

def save(force=False):
    """Save all registered libraries that have a filename and are marked dirty.

    If force = True save all of them blocking, else save non blocking and
    only if they were last saved more than 15 minutes ago.
    """
    global librarian

    print_d("Saving all libraries...")

    for lib in librarian.libraries.values():
        filename = lib.filename
        if not filename or not lib.dirty:
            continue

        if force:
            try: lib.save()
            except EnvironmentError: pass
            lib.destroy()
        elif (time.time() - util.mtime(filename)) > 15 * 60:  # 15 minutes
            threading.Thread(target=lib.save).run()
