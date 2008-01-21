# Copyright 2006-2007 Lukas Lalinsky
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gobject
import sys
import time
from quodlibet import config, const
from quodlibet.player import error as PlayerError
from quodlibet.player._base import BasePlayer
from quodlibet.player._xine import *

class XinePlaylistPlayer(BasePlayer):
    """Xine playlist player."""
    __gproperties__ = BasePlayer._gproperties_
    __gsignals__ = BasePlayer._gsignals_

    _paused = True

    def __init__(self, driver, librarian):
        super(XinePlaylistPlayer, self).__init__()
        self.name = "xine"
        self.version_info = "xine-lib: " + xine_get_version_string()
        _init_xine()
        self._supports_gapless = xine_check_version(1, 1, 1) == 1
        self._event_queue = None
        self._new_stream(driver)
        self._librarian = librarian

    def _new_stream(self, driver):
        global _xine
        self._audio_port = xine_open_audio_driver(_xine, driver, None)
        if not self._audio_port:
            raise PlayerError(
                _("Unable to create audio output"),
                _("The audio device %r was not found. Check your Xine "
                  "settings in ~/.quodlibet/config.") % driver)
        self._stream = xine_stream_new(_xine, self._audio_port, None)
        xine_set_param(self._stream, XINE_PARAM_IGNORE_VIDEO, 1)
        xine_set_param(self._stream, XINE_PARAM_IGNORE_SPU, 1)
        if self._supports_gapless:
            xine_set_param(self._stream, XINE_PARAM_EARLY_FINISHED_EVENT, 1)
        if self._event_queue:
            xine_event_dispose_queue(self._event_queue)
        self._event_queue = xine_event_new_queue(self._stream)
        xine_event_create_listener_thread(self._event_queue,
            self._event_listener, None)

    def destroy(self):
        global _xine
        if self._stream:
            xine_close(self._stream)
            xine_dispose(self._stream)
        if self._event_queue:
            xine_event_dispose_queue(self._event_queue)
        if self._audio_port:
            xine_close_audio_driver(_xine, self._audio_port)
        _exit_xine()
        super(BasePlayer, self).destroy()

    def _playback_finished(self):
        self._source.next_ended()
        self._end(False, gapless=True)
        return False

    def _update_metadata(self):
        if not self.song or not self.song.multisong:
            return False
        if self.info is self.song:
            self.info = type(self.song)(self.song["~filename"])
            self.info.multisong = False
        changed = False
        meta = [
            (XINE_META_INFO_TITLE, 'title'),
            (XINE_META_INFO_ARTIST, 'artist'),
            (XINE_META_INFO_ALBUM, 'album'),
        ]
        for info, name in meta:
            text = xine_get_meta_info(self._stream, info)
            if not text:
                continue
            text = text.decode('UTF-8', 'replace')
            if self.info.get(name) != text:
                self.info[name] = text
                changed = True
        if changed:
            self.emit('song-started', self.info)
            if self._librarian is not None:
                self._librarian.changed([self.song])
        return False

    def _event_listener(self, user_data, event):
        event = event.contents
        if event.type == XINE_EVENT_UI_PLAYBACK_FINISHED:
            gobject.idle_add(self._playback_finished,
                priority=gobject.PRIORITY_HIGH)
        elif event.type == XINE_EVENT_UI_SET_TITLE:
            gobject.idle_add(self._update_metadata,
                priority=gobject.PRIORITY_HIGH)
        elif event.type == XINE_EVENT_UI_MESSAGE:
            from ctypes import POINTER, cast, string_at, addressof
            msg = cast(event.data, POINTER(xine_ui_message_data_t)).contents
            if msg.type != XINE_MSG_NO_ERROR:
                if msg.explanation:
                    message = string_at(addressof(msg) + msg.explanation)
                else:
                    message = "xine error %s" % msg.type
                gobject.idle_add(self.error, message, True)
        return True

    def do_set_property(self, property, v):
        if property.name == 'volume':
            self._volume = v
            if self.song is not None:
                if config.getboolean("player", "replaygain"):
                    profiles = filter(None, self.replaygain_profiles)[0]
                    v = max(0.0, min(4.0, v * self.song.replay_gain(profiles)))
            v = min(100, int(v * 100))
            xine_set_param(self._stream, XINE_PARAM_AUDIO_VOLUME, v)
        else:
            raise AttributeError

    def get_position(self):
        """Return the current playback position in milliseconds,
        or 0 if no song is playing."""
        pos_stream, pos_time, length_time = xine_get_pos_length(self._stream)
        return pos_time

    def _stop(self):
        xine_stop(self._stream)

    def _pause(self):
        xine_set_param(self._stream, XINE_PARAM_SPEED, XINE_SPEED_PAUSE)

    def _play(self):
        if (xine_get_param(self._stream, XINE_PARAM_SPEED) !=
            XINE_SPEED_NORMAL):
            xine_set_param(self._stream, XINE_PARAM_SPEED, XINE_SPEED_NORMAL)
        if xine_get_status(self._stream) != XINE_STATUS_PLAY:
            xine_play(self._stream, 0, 0)

    def _set_paused(self, paused):
        if paused != self._paused:
            self._paused = paused
            if self.song:
                self.emit((paused and 'paused') or 'unpaused')
                if self._paused:
                    if not self.song.is_file:
                        self._stop()
                    else:
                        self._pause()
                else:
                    self._play()
            elif paused is True:
                # Something wants us to pause between songs, or when
                # we've got no song playing (probably StopAfterMenu).
                self.emit('paused')

    paused = property(lambda s: s._paused, _set_paused)

    def error(self, message, lock):
        self._stop()
        self.emit('error', self.song, message, lock)
        if not self.paused:
            self.next()

    def seek(self, pos):
        """Seek to a position in the song, in milliseconds."""
        if xine_get_param(self._stream, XINE_PARAM_SPEED) == XINE_SPEED_PAUSE:
            xine_play(self._stream, 0, int(pos))
            xine_set_param(self._stream, XINE_PARAM_SPEED, XINE_SPEED_PAUSE)
        else:
            xine_play(self._stream, 0, int(pos))
        self.emit('seek', self.song, pos)

    def _end(self, stopped, gapless=False):
        # We need to set self.song to None before calling our signal
        # handlers. Otherwise, if they try to end the song they're given
        # (e.g. by removing it), then we get in an infinite loop.
        song = self.song
        self.song = self.info = None
        self.emit('song-ended', song, stopped)

        # Then, set up the next song.
        self.song = self.info = self._source.current
        self.emit('song-started', self.song)

        if self.song is not None:
            if gapless and self._supports_gapless:
                xine_set_param(self._stream, XINE_PARAM_GAPLESS_SWITCH, 1)
            xine_open(self._stream, self.song("~uri"))
            if self._paused:
                self._pause()
            else:
                self._play()
            if gapless and self._supports_gapless:
                xine_set_param(self._stream, XINE_PARAM_GAPLESS_SWITCH, 0)
        else:
            self.paused = True
            xine_stop(self._stream)

_xine = None
_plugins = None

def _init_xine():
    global _xine, _plugins
    _xine = xine_new()
    if _xine:
        xine_config_load(_xine, xine_get_homedir() + "/.xine/config")
        xine_init(_xine)
        _plugins = []
        for plugin in xine_list_input_plugins(_xine):
            if not plugin:
                break
            _plugins.append(plugin.lower())

def _exit_xine():
    global _xine
    if _xine:
        xine_exit(_xine)

def can_play_uri(uri):
    global _xine, _plugins
    if _xine is None:
        _init_xine()
    for plugin in _plugins:
        if uri.startswith(plugin):
            return True
    return False

def init(librarian):
    try:
        driver = config.get("settings", "xine_driver")
    except:
        driver = None
    return XinePlaylistPlayer(driver, librarian)
