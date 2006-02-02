# Copyright 2004 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os, sys, locale
import config
import gobject, gst

os.environ['PYGTK_USE_GIL_STATE_API'] = '' # from jdahlin

class NoSinkError(ValueError): pass
class NoSourceError(ValueError): pass

def GStreamerSink(pipeline):
    """Try to create a GStreamer pipeline:
    * If requested, look the pipeline up in GConf.
    * Try making the pipeline.
    * If it fails, fall back to alsasink.
    * If that fails, fall back to osssink.
    * Otherwise, complain loudly."""

    if pipeline == "gconf":
        # We can't use gconfaudiosink/autoaudiosink -- querying its
        # current time fails.
        try: import gconf
        except ImportError: pipeline = "alsasink"
        else:
            c = gconf.client_get_default()
            val = c.get("/system/gstreamer/0.8/default/audiosink")
            if val.type == gconf.VALUE_STRING: pipeline = val.get_string()
            else: pipeline = "alsasink"

    try: pipe = gst.parse_launch(pipeline)
    except gobject.GError, err:
        if pipeline != "osssink":
            print "%r failed, falling back to osssink (%s)." % (pipeline, err)
            try: pipe = gst.parse_launch("osssink")
            except gobject.GError: pipe = None
            else: pipeline = "osssink"
        else: pipe = None
    locale.getlocale(locale.LC_NUMERIC)
    if pipe: return pipe, pipeline
    else: raise NoSinkError(pipeline)

class PlaylistPlayer(object):
    """Interfaces between a QL PlaylistModel and a GSt playbin."""

    __paused = False
    song = None
    info = None
    __length = 1
    __volume = 1.0

    def __init__(self, sinkname):
        device, sinkname = GStreamerSink(sinkname)
        self.name = sinkname
        self.bin = gst.element_factory_make('playbin')
        self.bin.set_property('video-sink', None)
        self.bin.set_property('audio-sink', device)
        self.__device = device
        bus = self.bin.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self.__message)
        #bus.connect_object('eos', self.__end, False)
        #self.bin.connect('found-tag', self.__tag)
        self.paused = True

    def __message(self, bus, message):
        if message.type == gst.MESSAGE_EOS:
            self.__end(False)
        elif message.type == gst.MESSAGE_TAG:
            self.__tag(message.parse_tag())
        elif message.type == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            self.info.error("%s" % err, debug)
        return True

    def setup(self, info, source, song):
        """Connect to a SongWatcher, a PlaylistModel, and load a song."""
        self.__source = source
        self.info = info
        self.go_to(song)

    def get_position(self):
        """Return the current playback position in milliseconds,
        or 0 if no song is playing."""
        if self.bin.get_property('uri'):
            p = self.bin.query_position(gst.FORMAT_TIME)[0]
            p //= gst.MSECOND
            return p
        else: return 0
        
    def __set_paused(self, paused):
        if paused != self.__paused:
            self.__paused = paused
            if self.info: self.info.set_paused(paused)
            if self.song:
                if self.__paused:
                   if not self.song.is_file:
                       self.bin.set_state(gst.STATE_NULL)
                   else: self.bin.set_state(gst.STATE_PAUSED)
                else: self.bin.set_state(gst.STATE_PLAYING)
    def __get_paused(self): return self.__paused
    paused = property(__get_paused, __set_paused)

    def set_volume(self, v):
        self.__volume = v
        if self.song is None: self.bin.set_property('volume', v)
        else:
            v = max(0.0, min(4.0, v * self.song.replay_gain()))
            self.bin.set_property('volume', v)
    def get_volume(self): return self.__volume
    volume = property(get_volume, set_volume)

    def error(self, code, lock):
        self.bin.set_property('uri', '')
        self.bin.set_state(gst.STATE_NULL)
        self.song = None
        self.paused = True
        self.info.error(code, lock)
        self.info.song_started(None)
        config.set("memory", "song", "")

    def __load_song(self, song, lock):
        # Under as-yet-undetermined conditions, the initial set_state()
        # can mysteriously fail -- if you turn GStreamer debugging on you
        # get diagnostics like this:
        #   alsa( 1481) gstalsa.c(1632):gst_alsa_open_audio:<alsasink0> 
        #   ALSA device "default" is already in use by another program.
        # 
        # This is believed to be a GStreamer bug. If it happens, try again
        # after pausing a little.
        st = self.bin.set_state(gst.STATE_NULL)
        if not st:
            import time
            time.sleep(0.01)
            st = self.bin.set_state(gst.STATE_NULL)
        if not st:
            self.error(_('GStreamer status not expected'), False)
            return

        self.bin.set_property('uri', song("~uri"))
        self.__length = song["~#length"] * 1000
        if self.__paused: st = self.bin.set_state(gst.STATE_PAUSED)
        else: st = self.bin.set_state(gst.STATE_PLAYING)
        if not st:
            self.error(_('GStreamer status not expected'), False)
            return

    def quit(self):
        """Shut down the playbin."""
        self.bin.set_state(gst.STATE_NULL)

    def seek(self, pos):
        """Seek to a position in the song, in milliseconds."""
        if self.bin.get_property('uri'):
            pos = max(0, int(pos))
            if pos >= self.__length:
                self.paused = True
                pos = self.__length

            gst_time = pos * gst.MSECOND
            event = gst.event_new_seek(
                1.0, gst.FORMAT_TIME, gst.SEEK_FLAG_FLUSH,
                gst.SEEK_TYPE_SET, gst_time, gst.SEEK_TYPE_NONE, 0)
            if self.bin.send_event(event):
                self.info.seek(self.song, pos)

    def remove(self, song):
        if self.song is song: self.__end(False)

    def __get_song(self, lock=False):
        song = self.__source.current
        self.song = song
        self.info.song_started(song)
        self.volume = self.__volume
        if song is not None:
            config.set("memory", "song", song["~filename"])
            self.__load_song(song, lock)
        else:
            config.set("memory", "song", "")
            self.paused = True
            self.bin.set_state(gst.STATE_NULL)
            self.bin.set_property('uri', '')

    def __end(self, stopped=True):
        self.info.song_ended(self.song, stopped)
        self.song = None
        if not stopped:
            self.__source.next_ended()
            self.__get_song(True)

    def __tag(self, tags):
        if self.song and self.song.fill_metadata:
            if self.song.multisong:
                proxy = type(self.song)(self.song["~filename"])
                proxy.multisong = False
                proxy.update(self.song)
            else: proxy = self.song

            changed = False
            for k in tags.keys():
                value = str(tags[k]).strip()
                if not value: continue
                if k == "bitrate":
                    try: bitrate = int(value)
                    except (ValueError, TypeError): pass
                    else:
                        if bitrate != self.song.get("~#bitrate"):
                            changed = True
                            proxy["~#bitrate"] = bitrate
                elif k == "duration":
                    try: length = int(long(value) / gst.SECOND)
                    except (ValueError, TypeError): pass
                    else:
                        if length != self.song.get("~#length"):
                            changed = True
                            proxy["~#length"] = length
                elif k in ["emphasis", "mode", "layer"]: continue
                elif isinstance(value, basestring):
                    value = unicode(value, errors='replace')
                    k = {"track-number": "tracknumber",
                         "location": "website"}.get(k, k)
                    if proxy.get(k) == value: continue
                    # If the title changes for a stream, we want to change
                    # *only* the proxy.
                    elif k == "title":
                        if value == self.info.song.get("title"): continue
                        elif self.song.multisong: proxy[k] = value
                    # Otherwise, if any other tag changes, or the song isn't
                    # a stream, change the actual song.
                    else: self.song[k] = value
                    changed = True

            if changed:
                if self.song.multisong: self.info.song_started(proxy)
                else: self.info.changed([proxy])

    def reset(self):
        self.__source.reset()

    def next(self):
        self.__source.next()
        self.__end()
        self.__get_song()
        if self.song: self.paused = False

    def previous(self):
        self.__source.previous()
        self.__end()
        self.__get_song()
        if self.song: self.paused = False

    def go_to(self, song):
        self.__source.go_to(song)
        self.__end()
        self.__get_song()

global playlist
playlist = None

def init(pipeline):
    gst.debug_set_default_threshold(gst.LEVEL_ERROR)
    if gst.element_make_from_uri(gst.URI_SRC, "file://", ""):
        global playlist
        playlist = PlaylistPlayer(pipeline or "gconfaudiosink")
        return playlist
    else: raise NoSourceError
