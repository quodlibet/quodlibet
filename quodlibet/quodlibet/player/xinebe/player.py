# -*- coding: utf-8 -*-
# Copyright 2006-2007 Lukas Lalinsky
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import GLib

from quodlibet import _
from quodlibet import config
from quodlibet.player import PlayerError
from quodlibet.player._base import BasePlayer
from quodlibet.util.string import decode

from . import cdefs
from .cdefs import XINE_PARAM_SPEED, XINE_PARAM_GAPLESS_SWITCH, xine_dispose, \
    XINE_SPEED_PAUSE, xine_play, xine_close, xine_set_param, xine_get_param, \
    xine_get_status, xine_open, xine_stop, XINE_PARAM_EARLY_FINISHED_EVENT, \
    XINE_META_INFO_ARTIST, xine_ui_message_data_t, XINE_EVENT_UI_SET_TITLE, \
    XINE_PARAM_AUDIO_AMP_MUTE, XINE_PARAM_AUDIO_AMP_LEVEL, xine_new, \
    XINE_EVENT_UI_PLAYBACK_FINISHED, xine_event_dispose_queue, xine_init, \
    XINE_PARAM_IGNORE_VIDEO, XINE_PARAM_IGNORE_SPU, xine_config_load, \
    xine_check_version, xine_get_homedir, xine_list_input_plugins, xine_exit, \
    xine_open_audio_driver, xine_close_audio_driver, XINE_STATUS_PLAY, \
    XINE_SPEED_NORMAL, xine_get_pos_length, XINE_MSG_NO_ERROR, \
    XINE_EVENT_UI_MESSAGE, xine_get_meta_info, XINE_META_INFO_ALBUM, \
    XINE_META_INFO_TITLE, xine_stream_new, xine_get_version_string, \
    xine_event_new_queue, xine_event_create_listener_thread


class XineHandle(object):
    def __init__(self):
        _xine = xine_new()
        xine_config_load(_xine, xine_get_homedir() + b"/.xine/config")
        xine_init(_xine)
        self._xine = _xine

    def list_input_plugins(self):
        """
        Returns:
            List[text_type]
        """

        plugins = []
        for plugin in xine_list_input_plugins(self._xine):
            if not plugin:
                break
            plugins.append(decode(plugin))
        return plugins

    def exit(self):
        xine_exit(self._xine)

    def open_audio_driver(self, identifier, data):
        return xine_open_audio_driver(self._xine, identifier, data)

    def close_audio_driver(self, driver):
        xine_close_audio_driver(self._xine, driver)

    def stream_new(self, audio_port, video_port):
        return xine_stream_new(self._xine, audio_port, video_port)


class XinePlaylistPlayer(BasePlayer):
    """Xine playlist player."""

    _paused = True

    def __init__(self, driver, librarian):
        """May raise PlayerError"""

        super(XinePlaylistPlayer, self).__init__()
        self.name = "xine"
        self.version_info = "xine-lib: " + decode(xine_get_version_string())
        self._volume = 1.0
        self._handle = XineHandle()
        self._supports_gapless = xine_check_version(1, 1, 1) == 1
        self._event_queue = None

        self._new_stream(driver)
        self._librarian = librarian
        self._destroyed = False

    def _new_stream(self, driver):
        assert driver is None or isinstance(driver, bytes)
        self._audio_port = self._handle.open_audio_driver(driver, None)
        if not self._audio_port:
            raise PlayerError(
                _("Unable to create audio output"),
                _("The audio device %r was not found. Check your Xine "
                  "settings in ~/.quodlibet/config.") % driver)
        self._stream = self._handle.stream_new(self._audio_port, None)
        xine_set_param(self._stream, XINE_PARAM_IGNORE_VIDEO, 1)
        xine_set_param(self._stream, XINE_PARAM_IGNORE_SPU, 1)
        self.update_eq_values()
        if self._supports_gapless:
            xine_set_param(self._stream, XINE_PARAM_EARLY_FINISHED_EVENT, 1)
        if self._event_queue:
            xine_event_dispose_queue(self._event_queue)
        self._event_queue = xine_event_new_queue(self._stream)
        xine_event_create_listener_thread(self._event_queue,
            self._event_listener, None)

    def _destroy(self):
        self._destroyed = True

        if self._stream:
            xine_close(self._stream)
            xine_dispose(self._stream)
            self._stream = None
        if self._event_queue:
            xine_event_dispose_queue(self._event_queue)
        if self._audio_port:
            self._handle.close_audio_driver(self._audio_port)
        self._handle.exit()

    def _playback_finished(self):
        if self._destroyed:
            return False

        self._source.next_ended()
        self._end(False, None, gapless=True)
        return False

    def _update_metadata(self):
        if self._destroyed:
            return False

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
            GLib.idle_add(self._playback_finished,
                priority=GLib.PRIORITY_HIGH)
        elif event.type == XINE_EVENT_UI_SET_TITLE:
            GLib.idle_add(self._update_metadata,
                priority=GLib.PRIORITY_HIGH)
        elif event.type == XINE_EVENT_UI_MESSAGE:
            from ctypes import POINTER, cast, string_at, addressof
            msg = cast(event.data, POINTER(xine_ui_message_data_t)).contents
            if msg.type != XINE_MSG_NO_ERROR:
                if msg.explanation:
                    message = string_at(addressof(msg) + msg.explanation)
                else:
                    message = "xine error %s" % msg.type
                message = message.decode("utf-8", errors="replace")
                GLib.idle_add(self._error, PlayerError(message))
        return True

    def do_get_property(self, property):
        if property.name == 'volume':
            return self._volume
        elif property.name == 'seekable':
            if self.song is None:
                return False
            return True
        elif property.name == 'mute':
            if not self._destroyed:
                return xine_get_param(self._stream, XINE_PARAM_AUDIO_AMP_MUTE)
            return False
        else:
            raise AttributeError

    def do_set_property(self, property, v):
        if property.name == 'volume':
            self._volume = v
            v = self.calc_replaygain_volume(v)
            v = min(100, int(v * 100))
            if not self._destroyed:
                xine_set_param(self._stream, XINE_PARAM_AUDIO_AMP_LEVEL, v)
        elif property.name == 'mute':
            if not self._destroyed:
                xine_set_param(self._stream, XINE_PARAM_AUDIO_AMP_MUTE, v)
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

    @property
    def paused(self):
        return self._paused

    @paused.setter
    def paused(self, paused):
        if paused == self._paused:
            return
        self._paused = paused
        self.emit((paused and 'paused') or 'unpaused')
        if self._paused != paused:
            return

        if self.song:
            if paused:
                if not self.song.is_file:
                    xine_close(self._stream)
                    xine_open(self._stream, self.song("~uri"))
                else:
                    self._pause()
            else:
                self._play()

    def _error(self, player_error=None):
        if self._destroyed:
            return False

        if self.error:
            return False

        self.error = True
        self.paused = True
        if player_error:
            self.emit('error', self.song, player_error)

    def seek(self, pos):
        """Seek to a position in the song, in milliseconds."""
        if xine_get_param(self._stream, XINE_PARAM_SPEED) == XINE_SPEED_PAUSE:
            xine_play(self._stream, 0, int(pos))
            xine_set_param(self._stream, XINE_PARAM_SPEED, XINE_SPEED_PAUSE)
        else:
            xine_play(self._stream, 0, int(pos))
        self.emit('seek', self.song, pos)

    def _end(self, stopped, next_song=None, gapless=False):
        # We need to set self.song to None before calling our signal
        # handlers. Otherwise, if they try to end the song they're given
        # (e.g. by removing it), then we get in an infinite loop.
        song = self.song
        self.song = self.info = None
        self.emit('song-ended', song, stopped)

        # reset error state
        self.error = False

        current = self._source.current if next_song is None else next_song

        # Then, set up the next song.
        self.song = self.info = current
        self.emit('song-started', self.song)

        if self.song is not None:
            self.volume = self.volume
            if gapless and self._supports_gapless:
                xine_set_param(self._stream, XINE_PARAM_GAPLESS_SWITCH, 1)
            xine_open(self._stream, self.song("~uri").encode("ascii"))
            if self._paused:
                self._pause()
            else:
                if song is None:
                    self.emit("unpaused")
                self._play()
            if gapless and self._supports_gapless:
                xine_set_param(self._stream, XINE_PARAM_GAPLESS_SWITCH, 0)
        else:
            self.paused = True
            xine_stop(self._stream)

        # seekable might change if we change to None, so notify just in case
        self.notify("seekable")

    def setup(self, playlist, song, seek_pos):
        super(XinePlaylistPlayer, self).setup(playlist, song, seek_pos)
        # xine's declining to seek so soon after startup; try again in 100ms
        if seek_pos:
            GLib.timeout_add(100, self.seek, seek_pos)

    @property
    def eq_bands(self):
        # These are taken straight from Xine's API
        return [30, 60, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]

    def update_eq_values(self):
        bands = self.eq_bands
        need_eq = any(self._eq_values)
        for band, val in enumerate(self._eq_values):
            param = getattr(cdefs, 'XINE_PARAM_EQ_%dHZ' % bands[band])
            # between 1..200; 100 is the default gain; 0 means no EQ filter
            # only negative gain seems to work
            val = (int(val * 100 / 24.0) + 100) or 1
            val *= int(need_eq)
            xine_set_param(self._stream, param, val)

    def can_play_uri(self, uri):
        for plugin in self._handle.list_input_plugins():
            if uri.startswith(plugin.lower()):
                return True
        return False


def init(librarian):
    """May raise PlayerError"""

    try:
        driver = config.getbytes("settings", "xine_driver")
    except:
        driver = None
    return XinePlaylistPlayer(driver, librarian)
