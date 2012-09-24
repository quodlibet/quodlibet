# Copyright 2004 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet.player._base import BasePlayer
from quodlibet.qltk.songlist import PlaylistModel

class NullPlayer(BasePlayer):
    __gproperties__ = BasePlayer._gproperties_
    __gsignals__ = BasePlayer._gsignals_
    version_info = "Null Player Backend"
    name = "Null"

    def __init__(self, sinkname="", librarian=None):
        super(NullPlayer, self).__init__()
        self._set_paused(True)
        self._source = PlaylistModel()

    def get_position(self):
        """Return the current playback position in milliseconds,
        or 0 if no song is playing."""
        return 0

    def _set_paused(self, paused):
        if paused != self._paused:
            self._paused = paused
            if self.song:
                self.emit((paused and 'paused') or 'unpaused')
            elif paused is True:
                # Something wants us to pause between songs, or when
                # we've got no song playing (probably StopAfterMenu).
                self.emit('paused')
    def _get_paused(self): return self._paused
    paused = property(_get_paused, _set_paused)

    def do_set_property(self, property, v):
        if property.name == 'volume':
            self._volume = v
        else:
            raise AttributeError

    def error(self, message):
        self.emit('error', self.song, message)
        if not self.paused:
            self.next()

    def seek(self, pos):
        """Seek to a position in the song, in milliseconds."""
        if self.song:
            self.emit('seek', self.song, pos)

    def _end(self, stopped):
        # We need to set self.song to None before calling our signal
        # handlers. Otherwise, if they try to end the song they're given
        # (e.g. by removing it), then we get in an infinite loop.
        song = self.song
        self.song = self.info = None
        self.emit('song-ended', song, stopped)

        # Then, set up the next song.
        self.song = self.info = self._source.current
        self.emit('song-started', self.song)

        if self.song is None:
            self.paused = True

def can_play_uri(uri):
    return False

def init(librarian):
    return NullPlayer(librarian)

