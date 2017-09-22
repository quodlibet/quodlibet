# -*- coding: utf-8 -*-
# Copyright 2004 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet.player._base import BasePlayer
from quodlibet.player import PlayerError


class NullPlayer(BasePlayer):
    version_info = "Null Player Backend"
    name = "Null"

    def __init__(self, sinkname="", librarian=None):
        super(NullPlayer, self).__init__()
        self._paused = True
        self._source = None
        self._volume = 1.0
        self._mute = False
        self._position = 0

    def _destroy(self):
        pass

    def get_position(self):
        """Return the current playback position in milliseconds,
        or 0 if no song is playing."""
        return self._position

    @property
    def paused(self):
        return self._paused

    @paused.setter
    def paused(self, paused):
        if paused == self._paused:
            return
        self._paused = paused
        self.emit((paused and 'paused') or 'unpaused')

    def do_get_property(self, property):
        if property.name == 'volume':
            return self._volume
        elif property.name == 'seekable':
            if self.song is None:
                return False
            return True
        elif property.name == 'mute':
            return self._mute
        else:
            raise AttributeError

    def do_set_property(self, property, v):
        if property.name == 'volume':
            self._volume = v
        elif property.name == 'mute':
            self._mute = v
        else:
            raise AttributeError

    def _error(self, message):
        self.paused = True
        self.emit('error', self.song, PlayerError(message))

    def seek(self, pos):
        """Seek to a position in the song, in milliseconds."""

        self._position = pos
        if self.song:
            self.emit('seek', self.song, pos)

    def _end(self, stopped, next_song=None):
        # We need to set self.song to None before calling our signal
        # handlers. Otherwise, if they try to end the song they're given
        # (e.g. by removing it), then we get in an infinite loop.
        song = self.song
        self.song = self.info = None
        self.emit('song-ended', song, stopped)

        current = self._source.current if next_song is None else next_song

        # Then, set up the next song.
        self._position = 0
        self.song = self.info = current
        self.emit('song-started', self.song)

        if self.song is None:
            self.paused = True

        if not self.paused and song is None:
            self.emit("unpaused")

        # seekable might change if we change to None, so notify just in case
        self.notify("seekable")

    def can_play_uri(self, uri):
        return True


def init(librarian):
    return NullPlayer(librarian)
