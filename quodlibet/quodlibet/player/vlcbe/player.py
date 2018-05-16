# -*- coding: utf-8 -*-
# Copyright 2018 David Morris
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

################################################################################
#
# VLC Backend
#
# This is a backend for the VLC media player using their python interface
# "python-vlc" available on PyPi and licensed under the GPL.
#
################################################################################

from gi.repository import GLib

from quodlibet import _
from quodlibet import config
from quodlibet.player import PlayerError
from quodlibet.player._base import BasePlayer
from quodlibet.util.string import decode
from quodlibet.util import print_d

import vlc

class VLCPlayer(BasePlayer):
    _paused     = True
    _vlcmp      = None
    _volume     = 1.0
    _seekOnPlay = None

    def __init__(self, librarian=None):
        super().__init__()
        self._librarian = librarian

    @property
    def paused(self):
        return self._paused

    @paused.setter
    def paused(self, state):
        print_d(f"Pause State [{state}] pauseable [{self._vlcmp.can_pause()}]")

        # Detect if pause is not possible and alter the action accordingly
        if self._vlcmp is None or self._vlcmp.can_pause() == 0:
            print_d("Unable To Pause")
            state = True

        # Change the internal tracking
        prev_state   = self._paused
        self._paused = state

        # Only emit a signal if the pause state changed
        if state != prev_state:
            # Emit a signal telling the application a pause/unpause has occurred
            self.emit((self._paused and 'paused') or 'unpaused')

        # The signal handler might have changed the paused state
        # ... no matter what happens, set VLC to the current tracked pause state
        self._vlcmp.set_pause(self._paused)
        print_d(f"Performing Pause: {self._paused}")

    def do_get_property(self, property):
        if property.name == 'volume':
            return self._volume
        elif property.name == 'seekable':
            if self.song is None:
                return False
            return True
        elif property.name == 'mute':
            if self._vlcmp is not None:
                isMuted = self._vlcmp.audio_get_mute()
                muteStates = {-1:False, 0:False, 1:True}
                return muteStates[isMuted]
            return False
        else:
            raise AttributeError

    def do_set_property(self, property, v):
        if property.name == 'volume':
            self._volume = v
            if self._vlcmp is not None:
                v = self.calc_replaygain_volume(v)
                v = min(100, int(v * 100))
                self._vlcmp.audio_set_volume(v)
        elif property.name == 'mute':
            if self._vlcmp is not None:
                self._vlcmp.audio_set_mute(v)
        else:
            raise AttributeError


    def _destroy(self):
        """Clean up"""
        if self._vlcmp is not None:
            self._vlcmp.release()
            self._vlcmp  = None
            self._events = None

    def _end(self, stopped, next_song=None):
        """Start playing the current song from the source or
        next_song if it isn't None.
        """
        print_d("End song")
        song, info = self.song, self.info

        if self._vlcmp is not None:
            if self._vlcmp.get_state() in [vlc.State.Playing, vlc.State.Paused]:
                self._vlcmp.stop()
            self._vlcmp  = None
            self._events = None

        # We need to set self.song to None before calling our signal
        # handlers. Otherwise, if they try to end the song they're given
        # (e.g. by removing it), then we get in an infinite loop.
        self.song = self.info = None
        if song is not info:
            self.emit('song-ended', info, stopped)
        self.emit('song-ended', song, stopped)

        current = self._source.current if next_song is None else next_song

        # Then, set up the next song.
        self.song = self.info = current

        if self.song is not None:
            print_d("Next Song: %s" % self.song("~uri"))

            self.volume  = self.volume
            self._vlcmp  = vlc.MediaPlayer(self.song("~uri"))
            self._events = self._vlcmp.event_manager()
            self._events.event_attach(vlc.EventType.MediaPlayerPlaying, self._event_playing)
            self._events.event_attach(vlc.EventType.MediaPlayerEndReached, self._event_ended)
            self._vlcmp.play()
        else:
            self._vlcmp  = None
            self._events = None

        self.emit('song-started', self.song)
        self.notify("seekable")

    def setup(self, playlist, song, seek_pos):
        super().setup(playlist, song, seek_pos)
        # VLC cannot seek immediately at startup; try again in 100ms
        if seek_pos:
            GLib.timeout_add(100, self.seek, seek_pos)

    def _event_playing(self, event):
        print_d(f"Playing Event paused [{self._paused}] seek [{self._seekOnPlay}]")

        if self._paused:
            self.paused = self._paused

        # This should really be handled by the seekable event
        # ... However, it seems that when the seekable event is triggered, the length is not available
        if self._seekOnPlay is not None and self._vlcmp.is_seekable():
            self._vlcmp.set_position(self._seekOnPlay / self._vlcmp.get_length())
            self.emit('seek', self.song, self._seekOnPlay)
            self._seekOnPlay = None
            self.notify("seekable")

    def _event_ended(self, event):
        print_d(f"Playback Ended")
        if self._vlcmp is not None:
            self._vlcmp  = None
            self._events = None
        self._source.next_ended()
        self._end(False)

    def seek(self, position):
        """Seek to absolute position in milliseconds.
        If position is larger than the duration start the next song
        """

        if self._vlcmp is not None:
            # XXX Detect if we should skip to the next song !?!?
            if  self._vlcmp.get_state() == vlc.State.Paused:
                print_d(f"Seeking While Paused with seek [{position}]")
                self._vlcmp.set_position(position / self._vlcmp.get_length())
                self.emit('seek', self.song, position)
                # XXX Needed?
                #self._vlcmp.play()
            elif self._vlcmp.get_state() == vlc.State.Playing:
                print_d(f"Seeking While Playing with seek [{position}]")
                self._vlcmp.set_position(position / self._vlcmp.get_length())
                self.emit('seek', self.song, position)
            else:
                print_d(f"Seeking In State [{self._vlcmp.get_state()}] with seek [{position}]")
                self._vlcmp.stop()
                # VLC can only seek while playing so store the seek value for later
                self._seekOnPlay = position
                # Tell VLC to start playing
                # ... but the custom event handler will pause playback as necessary
                self._vlcmp.play()

    def get_position(self):
        """Return the current playback position in milliseconds,
        or 0 if no song is playing."""
        if self._vlcmp is not None and self._vlcmp.get_state() in [vlc.State.Playing, vlc.State.Paused]:
            return int(self._vlcmp.get_position() * self._vlcmp.get_length())
        else:
            return 0

    def can_play_uri(self, uri):
        """Whether the player supports playing the given URI scheme"""

        # XXX Implement Me!
        return True

def init(librarian):
    return VLCPlayer(librarian)
