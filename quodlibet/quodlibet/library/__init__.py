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

import quodlibet.formats as formats

from quodlibet.library.songs import SongFileLibrary, SongLibrary, SongLibrarian

librarian = library = None

def init(cache_fn=None, verbose=True):
    """Set up the library and return the main one.

    Create the 'global' main library, and also a librarian for
    all future SongLibraries.
    """
    global library, librarian
    s = ", ".join(formats.modules)
    if verbose: print_(string=_("Supported formats: %s") % s)
    SongFileLibrary.librarian = SongLibrary.librarian = SongLibrarian()
    library = SongFileLibrary("main")
    librarian = library.librarian
    if cache_fn:
        library.load(cache_fn, skip=formats.supported)
    return library
