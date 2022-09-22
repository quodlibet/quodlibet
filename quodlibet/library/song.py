# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
from pathlib import Path
from typing import Optional, Set, Iterable, TypeVar, Union

from quodlibet import util, print_d
from quodlibet.formats import MusicFile, AudioFile
from quodlibet.library.album import AlbumLibrary
from quodlibet.library.base import Library, PicklingMixin, K
from quodlibet.library.file import WatchedFileLibraryMixin
from quodlibet.library.playlist import PlaylistLibrary
from quodlibet.query import Query
from quodlibet.util.path import normalize_path
from senf import fsnative

V = TypeVar("V", bound=AudioFile)


class SongLibrary(Library[K, V], PicklingMixin):
    """A library for songs.

    Items in this kind of library must support (roughly) the AudioFile
    interface.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @util.cached_property
    def albums(self):
        return AlbumLibrary(self)

    @util.cached_property
    def playlists(self):
        pl_lib = PlaylistLibrary(self)
        print_d(f"Created playlist library {pl_lib}")
        return pl_lib

    def destroy(self):
        super().destroy()
        if "albums" in self.__dict__:
            self.albums.destroy()
        if "playlists" in self.__dict__:
            self.playlists.destroy()

    def tag_values(self, tag):
        """Return a set of all values for the given tag."""
        return {value for song in self.values()
                for value in song.list(tag)}

    def rename(self, song, new_name, changed: Optional[Set] = None):
        """Rename a song.

        This requires a special method because it can change the
        song's key.

        The 'changed' signal may fire for this library or the changed
        song is added to the passed changed set().

        If the song exists in multiple libraries you cannot use this
        method. Instead, use the librarian.
        """
        if song.key == new_name:
            print_d(f"Nothing changed for {new_name!r}")
            return
        print_d(f"Renaming {song.key!r} to {new_name!r}", self)
        del self._contents[song.key]
        song.rename(new_name)
        self._contents[song.key] = song
        if changed is not None:
            changed.add(song)
        else:
            self.changed({song})

    def query(self, text, sort=None, star=Query.STAR):
        """Query the library and return matching songs."""
        if isinstance(text, bytes):
            text = text.decode('utf-8')

        songs = self.values()
        if text != "":
            search = Query(text, star).search
            songs = [s for s in songs if search(s)]
        return songs


class SongFileLibrary(SongLibrary, WatchedFileLibraryMixin):
    """A library containing song files.
    Pickles contents to disk as `FileLibrary`"""

    def __init__(self, name=None, watch_dirs: Optional[Iterable[fsnative]] = None):
        print_d(f"Initializing {type(self)}: {name!r}")
        super().__init__(name)
        if watch_dirs:
            self.start_watching(watch_dirs)

    def get_filename(self, filename):
        key = normalize_path(filename, True)
        return self._contents.get(key)

    def add_filename(self,
                     filename: Union[str, Path],
                     add: bool = True) -> Optional[AudioFile]:
        """Add a song to the library based on filename.

        If 'add' is true, the song will be added and the 'added' signal
        may be fired.

        Example (add=False):
            load many songs and call Library.add(songs) to add all in one go.

        The song is returned if it is in the library after this call.
        Otherwise, None is returned.
        """

        key = normalize_path(filename, True)
        song = None
        if key not in self._contents:
            song = MusicFile(filename)
            if song and add:
                self.add([song])
        else:
            print_d(f"Already got file {filename!r}")
            song = self._contents[key]

        return song
