# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from typing import Iterable

from quodlibet import print_d
from quodlibet.library.base import Library
from quodlibet.util.collection import Playlist


class PlaylistLibrary(Library[str, Playlist]):
    """A PlaylistLibrary listens to a SongLibrary, and keeps tracks of playlists
    of these songs.

    The library behaves like a dictionary: the keys are playlist names,
    the values are Playlist objects.
    """

    def __init__(self, library):
        self.librarian = None

        super().__init__(f"{type(self).__name__} for {library._name}")
        print_d(f"Initializing Playlist Library {self} to watch {library._name!r}")

        self._library = library
        self._rsig = library.connect('removed', self.__songs_removed)
        self._csig = library.connect('changed', self.__songs_changed)

    def destroy(self):
        for sig in [self._asig, self._rsig, self._csig]:
            self._library.disconnect(sig)

    def remove(self, items: Iterable[Playlist]) -> Iterable[Playlist]:
        items = super().remove(items)
        for pl in items:
            pl.delete()
        return items

    def __songs_removed(self, library, songs):
        print_d(f"Removing {len(songs)} song(s) "
                f"across {len(self.playlists())} playlist(s) in {self}")
        changed = {
            playlist
            for playlist in self.playlists()
            if playlist.remove_songs(songs)
        }
        if changed:
            for pl in changed:
                pl.write()
            self.changed(changed)

    def __songs_changed(self, library, songs):
        changed = {
            playlist
            for playlist in self._contents.values()
            for song in songs
            if song in playlist.songs
        }
        if changed:
            for pl in changed:
                pl.write()
            self.changed(changed)
