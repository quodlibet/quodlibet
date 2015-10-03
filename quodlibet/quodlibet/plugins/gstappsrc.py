# -*- coding: utf-8 -*-
# Copyright 2015 Jarrad Whitaker
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gst
from quodlibet.player.gstbe.sources import GStreamerSource


class AppSrcPlugin(GStreamerSource):
    """AppSrc Plugins define an object which can interact with a GStreamer
    AppSrc. They can hence be used to output arbitrary audio content.

    Due to how GStreamer works, plugin initialization happens in two stages,
    first with Quodlibet's GStreamerPlayer and the playbin object, and secondly
    when the appsrc you can interface with has been created.

    Your plugin should periodically call the appsrc's push_buffer() method to
    send a Gst.Buffer of audio samples. At the least, the buffers you send need
    to have the fields

        buffer.duration (the duration, in nanoseconds, of the buffer), and
        buffer.pts (the time this buffer should be played, in nanoseconds,
                    relative to the start of the buffer)

    set.

    _enough_data() gets called when the appsrc's buffer is full and it is no
    longer accepting samples.

    _need_data() gets called when the appsrc's buffer is no longer full, and it
    can accept samples again.

    _seek_data(timeToSeekNS) gets called when the user wishes to seek to a
    particular time, in nanoseconds.

    play_song is called by the GStreamerPlayer when it has a song for you to
    play. You will want to call super() or set the uri to 'appsrc://' yourself,
    as this initializes the appsrc you will be interfacing with. Note that
    source_setup won't have been called on the first time play_song is called,
    as source_setup only gets called once the appsrc has been created. For this
    reason, you'll want to actually start playing song using _start_song.

    Finally, Quod Libet works out whether to use this plugin on a song by
    checking the protocol of the song's uri. It tests this with the
    handles_protocol() method of all loaded AppSrcPlugins, and will play the
    song with the first one that returns true. Hence, you'll want to either
    set the uri_protocol class member of your subclass, or override the
    handles_protocol method.

    """

    PLUGIN_INSTANCE = False
    uri_protocol = None

    # this gets called one the appsrc has been created.
    def source_setup(self, playbin, appsrc):
        self._appsrc = appsrc
        self._appsrc.set_property('format', Gst.Format.TIME)
        self._appsrc.connect('enough-data', self._enough_data)
        self._appsrc.connect('need-data', self._need_data)
        self._appsrc.connect('seek-data', self._seek_data)
        self._src_pad = self._appsrc.iterate_src_pads().next()[1]

    def __init__(self, player, playbin):
        self._player = player
        self._player.connect('song-ended', self._stop_song)
        self._player.connect('paused', self._pause)
        self._player.connect('unpaused', self._resume)

        # sometimes the playbin will be wrapped by a buffering manager
        self._playbin = playbin.bin if hasattr(playbin, 'bin') else playbin
        self._playbin.get_bus().connect('message', self._on_message)

        self._is_setup = False
        self._play_after_setup = None

        self._playbin.set_property('uri', 'appsrc://')
        self._playbin.connect('source-setup', self.source_setup)

    @classmethod
    def handles_protocol(Klass, protocol):
        return protocol and (protocol == Klass.uri_protocol)

    def _enough_data(self, *args):
        pass

    def _need_data(self, *args):
        pass

    def _seek_data(self, appsrc, seekNS):
        pass

    def _on_message(self, sender, message):
        pass

    def play_song(self, song):
        self._playbin.set_property('uri', 'appsrc://')
        if not self._is_setup:
            self._play_after_setup = lambda: self._start_song(song)
        else:
            self._start_song(song)

    def _start_song(self, song):
        pass

    def _pause(self, player):
        pass

    def _resume(self, player):
        pass

    def _song_ended(self):
        self._appsrc.end_of_stream()

    def _stop_song(self, player, song, is_stopped):
        pass
