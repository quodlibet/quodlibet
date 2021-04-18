# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
from typing import Iterable, Generator, Optional, Set

import quodlibet
from quodlibet import print_d, print_w
from quodlibet.formats import AudioFile
from quodlibet.library.base import Library
from quodlibet.util.collection import (Playlist, XSPFBackedPlaylist,
                                       FileBackedPlaylist)
from senf import text2fsn, _fsnative

_DEFAULT_PLAYLIST_DIR = text2fsn(os.path.join(quodlibet.get_user_dir(), "playlists"))
"""Directory for playlist files"""


class PlaylistLibrary(Library[str, Playlist]):
    """A PlaylistLibrary listens to a SongLibrary, and keeps tracks of playlists
    of these songs.

    The library behaves like a dictionary: the keys are playlist names,
    the values are Playlist objects.
    """

    def __init__(self, library: Library, pl_dir: _fsnative = _DEFAULT_PLAYLIST_DIR):
        self.librarian = None
        super().__init__(f"{type(self).__name__} for {library._name}")
        print_d(f"Initializing Playlist Library {self} to watch {library._name!r}")
        self.pl_dir = pl_dir
        if library is None:
            raise ValueError("Need a library to listen to")
        self._library = library
        self._read_playlists(library)

        self._rsig = library.connect('removed', self.__songs_removed)
        self._csig = library.connect('changed', self.__songs_changed)

    def _read_playlists(self, library):
        print_d(f"Reading playlist directory {self.pl_dir} (library: {library})")
        try:
            fns = os.listdir(self.pl_dir)
        except FileNotFoundError as e:
            print_w(f"No playlist dir found in {self.pl_dir!r}, creating. ({e})")
            os.mkdir(self.pl_dir)
            fns = []

        for fn in fns:
            if os.path.isdir(os.path.join(self.pl_dir, fn)):
                continue
            try:
                XSPFBackedPlaylist(self.pl_dir, text2fsn(fn),
                                   songs_lib=library, pl_lib=self)
            except TypeError as e:
                legacy = FileBackedPlaylist(self.pl_dir, text2fsn(fn),
                                            songs_lib=library, pl_lib=self)
                print_w(f"Converting {fn!r} to XSPF format ({e})")
                XSPFBackedPlaylist.from_playlist(legacy, songs_lib=library, pl_lib=self)
            except EnvironmentError:
                print_w("Invalid Playlist '%s'" % fn)

    def create(self, name_base: Optional[str] = None) -> Playlist:
        if name_base:
            return XSPFBackedPlaylist.new(self.pl_dir, name_base,
                                          songs_lib=self._library, pl_lib=self)
        return XSPFBackedPlaylist.new(self.pl_dir, songs_lib=self._library, pl_lib=self)

    def create_from_songs(self, songs: Iterable[AudioFile]) -> Playlist:
        """Creates a playlist visible to this library"""
        return XSPFBackedPlaylist.from_songs(self.pl_dir, songs, self._library, self)

    def destroy(self):
        for sig in [self._rsig, self._csig]:
            self._library.disconnect(sig)

    def playlists_featuring(self, song: AudioFile) -> Generator[Playlist, None, None]:
        """Returns a generator yielding playlists in which this song appears"""
        return (pl for pl in self if song in pl._list)

    def __songs_removed(self, library, songs):
        print_d(f"Removing {len(songs)} song(s) "
                f"across {len(self)} playlist(s) in {self}")
        changed = {pl for pl in self if pl.remove_songs(songs)}
        if changed:
            for pl in changed:
                pl.write()
            self.changed(changed)

    def __songs_changed(self, library, songs):
        # Q: what if the changes are entirely due to changes *from* this library?
        # A: seems safest to still emit 'changed' as collections can cache metadata etc
        changed = {
            playlist
            for playlist in self
            for song in songs
            if song in playlist.songs
        }
        if changed:
            # TODO: only write if anything *persisted* changes
            #  i.e. not internal stuff (notably: ~playlists itself)!
            for pl in changed:
                pl.finalize()
                pl.write()
            self.changed(changed)

    def recreate(self, playlist: Playlist, songs: Iterable[AudioFile]):
        """Keep a playlist but entirely replace its contents
        This is useful for applying new external sorting etc"""
        playlist._list.clear()
        playlist._list.extend(songs)
        playlist.finalize()
        playlist.write()
        self.changed([playlist])

    def add(self, items: Iterable[Playlist]) -> Set[Playlist]:
        print_d(f"Adding new playlist(s): {items}")
        return super().add(items)
