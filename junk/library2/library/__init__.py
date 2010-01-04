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

from library._library import Library, Librarian
from library.songs import SongFileLibrary, SongLibrary, SongLibrarian
