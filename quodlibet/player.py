# Copyright 2004 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os, sys
import config
import gobject, gst

os.environ['PYGTK_USE_GIL_STATE_API'] = '' # from jdahlin
gst.use_threads(True)

def GStreamerSink(pipeline):
    if pipeline == "gconf":
        # We can't use gconfaudiosink/autoaudiosink -- querying its
        # current time fails.
        try: import gconf
        except ImportError: sinkname = "alsasink"
        else:
            c = gconf.client_get_default()
            val = c.get("/system/gstreamer/0.8/default/audiosink")
            if val.type == gconf.VALUE_STRING: pipeline = val.get_string()
            else: pipeline = "alsasink"

    try: return gst.parse_launch(pipeline), pipeline
    except gobject.GError, err:
        if pipeline != "osssink":
            print "%r failed, falling back to osssink (%s)." % (pipeline, err)
            try: return gst.parse_launch("osssink"), "osssink"
            except gobject.GError: pass
    raise SystemExit("E: No valid GStreamer sinks found.\n"
                     "E: Set 'pipeline' in ~/.quodlibet/config.")

class PlaylistPlayer(object):
    __paused = False
    song = None
    __length = 1
    __volume = 1.0

    def __init__(self, device):
        device, pipeline = GStreamerSink(device)
        self.name = pipeline
        self.bin = gst.element_factory_make('playbin')
        self.bin.set_property('video-sink', None)
        self.bin.set_property('audio-sink', device)
        self.__device = device
        self.bin.connect_object('eos', self.__end, False)
        self.bin.connect('found-tag', self.__tag)
        self.paused = True

    def setup(self, info, source, song):
        self.__source = source
        self.info = info
        self.go_to(song)

    def get_position(self):
        if self.bin.get_property('uri'):
            p = self.bin.query(gst.QUERY_POSITION, gst.FORMAT_TIME)
            p //= gst.MSECOND
            return p
        else: return 0
        
    def __set_paused(self, paused):
        if paused != self.__paused:
            self.__paused = paused
            try: self.info.set_paused(paused)
            except AttributeError: pass
            if self.bin.get_property('uri'):
                if self.__paused: self.bin.set_state(gst.STATE_PAUSED)
                else: self.bin.set_state(gst.STATE_PLAYING)
    def __get_paused(self): return self.__paused
    paused = property(__get_paused, __set_paused)

    def set_volume(self, v):
        self.__volume = v
        if self.song is None: self.bin.set_property('volume', v)
        else: self.bin.set_property('volume', v * self.song.replay_gain())
    def get_volume(self): return self.__volume
    volume = property(get_volume, set_volume)

    def __load_song(self, song):
        self.bin.set_state(gst.STATE_NULL)
        self.bin.set_property('uri', song("~uri"))
        self.__length = song["~#length"] * 1000
        if self.__paused: self.bin.set_state(gst.STATE_PAUSED)
        else: self.bin.set_state(gst.STATE_PLAYING)

    def quit(self):
        self.bin.set_state(gst.STATE_NULL)

    def seek(self, pos):
        if self.bin.get_property('uri'):
            pos = max(0, int(pos))
            if pos >= self.__length:
                self.paused = True
                pos = self.__length

            ms = pos * gst.MSECOND
            event = gst.event_new_seek(
                gst.FORMAT_TIME|gst.SEEK_METHOD_SET|gst.SEEK_FLAG_FLUSH, ms)
            self.bin.send_event(event)
            self.info.seek(self.song, pos)

    def remove(self, song):
        if self.song is song: self.__end(False)

    def __get_song(self):
        song = self.__source.current
        if song is not None:
            config.set("memory", "song", song["~filename"])
            try: self.__load_song(song)
            except Exception, err:
                sys.stderr.write(str(err) + "\n")
                self.info.missing(song)
                self.next()
                self.paused = True
                return
        else:
            self.paused = True
            self.bin.set_state(gst.STATE_NULL)
        self.song = song
        self.info.song_started(song)
        self.volume = self.__volume

    def __end(self, stopped=True):
        self.info.song_ended(self.song, stopped)
        self.song = None
        if not stopped:
            self.__source.next()
            # Avoids a deadlock if the song ends and the user presses a
            # a button that calls __end at the same time; both threads
            # end up waiting for something inside GSt.
            gobject.idle_add(self.__get_song)

    def __tag(self, pipeline, source, tags):
        if getattr(self.song, 'stream', False):
            for k in tags.keys():
                value = str(tags[k]).strip()
                if not value: continue
                if k == "location": k = "website"
                if k in ["website", "genre", "comment"]:
                    self.song[k] = unicode(value, errors='replace')
                if k == "bitrate":
                    try: self.song["~#bitrate"] = int(value)
                    except ValueError: pass
            fakesong = type(self.song)(self.song["~filename"])
            fakesong.update(self.song)
            if "title" in tags.keys():
                fakesong["title"] = unicode(tags["title"], errors='replace')
            for k in tags.keys():
                if self.info.song.get(k) != fakesong.get(k):
                    self.info.song_started(fakesong)
                    break

    def reset(self):
        self.__source.reset()

    def next(self):
        self.__end()
        self.paused = False
        self.__source.next()
        self.__get_song()

    def previous(self):
        self.paused = False
        self.__source.previous()
        self.__end()
        self.__get_song()

    def go_to(self, song):
        self.__source.go_to(song)
        self.__end()
        self.__get_song()

global playlist
playlist = None

def init(pipeline):
    global playlist
    playlist = PlaylistPlayer(pipeline or "gconf")
    return playlist
