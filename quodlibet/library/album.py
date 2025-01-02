# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import print_d
from quodlibet.formats._audio import AlbumKey
from quodlibet.library.base import Library
from quodlibet.util.collection import Album


class AlbumLibrary(Library[AlbumKey, Album]):
    """An AlbumLibrary listens to a SongLibrary and sorts its songs into
    albums.

    The library behaves like a dictionary: the keys are album_keys of
    AudioFiles, the values are Album objects.
    """

    def __init__(self, library):
        self.librarian = None
        print_d("Initializing Album Library to watch %r" % library._name)

        super().__init__("AlbumLibrary for %s" % library._name)

        self._library = library
        self._asig = library.connect("added", self.__added)
        self._rsig = library.connect("removed", self.__removed)
        self._csig = library.connect("changed", self.__changed)
        self.__added(library, library.values(), signal=False)

    def load(self):
        # deprecated
        pass

    def destroy(self):
        for sig in [self._asig, self._rsig, self._csig]:
            self._library.disconnect(sig)

    def _get(self, item):
        return self._contents.get(item)

    def __add(self, items):
        changed = set()
        new = set()
        for song in items:
            key = song.album_key
            if key in self._contents:
                changed.add(self._contents[key])
            else:
                album = Album(song)
                self._contents[key] = album
                new.add(album)
            self._contents[key].songs.add(song)

        changed -= new
        return changed, new

    def __added(self, library, items, signal=True):
        changed, new = self.__add(items)

        for album in changed:
            album.finalize()

        if signal:
            if new:
                self.emit("added", new)
            if changed:
                self.emit("changed", changed)

    def __removed(self, library, items):
        changed = set()
        removed = set()
        for song in items:
            key = song.album_key
            album = self._contents[key]
            album.songs.remove(song)
            changed.add(album)
            if not album.songs:
                removed.add(album)
                del self._contents[key]

        changed -= removed

        for album in changed:
            album.finalize()

        if removed:
            self.emit("removed", removed)
        if changed:
            self.emit("changed", changed)

    def __changed(self, library, items):
        """Album keys could change between already existing ones... so we
        have to do it the hard way and search by id."""
        print_d("Updating affected albums for %d items" % len(items))
        changed = set()
        removed = set()
        to_add = []
        for song in items:
            # in case the key hasn't changed
            key = song.album_key
            if key in self._contents and song in self._contents[key].songs:
                changed.add(self._contents[key])
            else:  # key changed... look for it in each album
                to_add.append(song)
                for album in self._contents.values():
                    if song in album.songs:
                        album.songs.remove(song)
                        if not album.songs:
                            removed.add(album)
                        else:
                            changed.add(album)
                        break

        # get new albums and changed ones because keys could have changed
        add_changed, new = self.__add(to_add)
        changed |= add_changed

        # check if albums that were empty at some point are still empty
        for album in removed:
            if not album.songs:
                del self._contents[album.key]
                changed.discard(album)

        for album in changed:
            album.finalize()

        if removed:
            self.emit("removed", removed)
        if changed:
            self.emit("changed", changed)
        if new:
            self.emit("added", new)
