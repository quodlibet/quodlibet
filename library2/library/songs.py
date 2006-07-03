# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

"""Song library classes.

These libraries require their items to be AudioFiles, or something
close enough.
"""

import traceback

from library._library import Library, Librarian

class SongLibrarian(Librarian):
    """A librarian for SongLibraries."""

    def tag_values(self, tag):
        """Return a list of all values for the given tag."""
        tags = set()
        for library in self.libraries.itervalues():
            tags.update(library.tag_values(tag))
        return list(tags)

    def rename(self, song, newname):
        """Rename the song in all libraries it belongs to."""
        # This needs to poke around inside the library directly.  If
        # it uses add/remove to handle the songs it fires incorrect
        # signals. If it uses the library's rename method, it breaks
        # the call for future libraries because the item's key has
        # changed. So, it needs to reimplement the method.
        re_add = []
        for library in self.libraries.itervalues():
            if song.key in library:
                del(library._contents[song.key])
                re_add.append(library)
        song.rename(newname)
        for library in re_add:
            library._contents[song.key] = song
            library.changed([song])

class SongLibrary(Library):
    """A library for songs.

    Items in this kind of library must support (roughly) the AudioFile
    interface.
    """

    def tag_values(self, tag):
        """Return a list of all values for the given tag."""
        tags = set()
        for song in self.values():
            tags.update(song.list(tag))
        return list(tags)

    def rename(self, song, newname):
        """Rename a song.

        This requires a special method because it can change the
        song's key.
        """
        del(self._contents[song.key])
        song.rename(newname)
        self._contents[song.key] = song
        self.changed([song])

class SongFileLibrary(SongLibrary):
    """A library containing song files on a local filesystem."""

    def _load(self, song):
        # Check to see if the song is still on the filesystem, and
        # if it's mtime has changed.
        if song.valid():
            self._contents[song.key] = song
            return False, False
        elif song.exists():
            try:
                song.reload()
            except StandardError:
                traceback.print_exc()
                return False, True
            else:
                self._contents[song.key] = song
                return True, False
        elif not song.mounted():
            self._masked.setdefault(song.mountpoint, {})
            self._masked[song.mountpoint][song.key] = song
            return False, False
        else:
            return False, False
