# Copyright 2004 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os, sys
import time
import threading
import config
import gst

def GStreamerSink(sinkname):
    if sinkname == "gconf":
        try: import gconf
        except ImportError: sinkname = "osssink"
        else:
            c = gconf.client_get_default()
            val = c.get("/system/gstreamer/0.8/default/audiosink")
            if val.type == gconf.VALUE_STRING: sinkname = val.get_string()
            else: sinkname = "osssink"

    s = gst.element_factory_make(sinkname, 'sink')
    if s: return s
    elif sinkname != "osssink":
        return gst.element_factory_make("osssink", 'sink')
    else:
        raise SystemExit("No valid GStreamer sinks found.")

class PlaylistPlayer(object):
    __paused = False
    __song = None
    __length = 1
    __volume = 1.0
    bin = None

    def __init__(self, device):
        self.__device = device
        self.paused = True

    def setup(self, info, source, song):
        self.__source = source
        self.info = info
        self.go_to(song)

    def __update_time(self):
        if self.bin is None:
            self.__info.time = (0, 1)
        else:
            pos = self.bin.query(gst.QUERY_POSITION, gst.FORMAT_TIME)
            len = self.bin.query(gst.QUERY_TOTAL, gst.FORMAT_TIME)
            self.info.time = (pos // gst.MSECOND, len // gst.MSECOND)

    def __iter__(self): return iter(self.__source)

    def __set_paused(self, paused):
        if paused != self.__paused:
            self.__paused = paused
            try: self.info.set_paused(paused)
            except AttributeError: pass
            state = ((paused and gst.STATE_PAUSED) or gst.STATE_PLAYING)
            try: self.bin.set_state(state)
            except AttributeError: pass
    def __get_paused(self): return self.__paused
    paused = property(__get_paused, __set_paused)

    def set_volume(self, v):
        self.__volume = v
        try: self.bin.set_property('volume', v)
        except AttributeError: pass
    def get_volume(self): return self.__volume
    volume = property(get_volume, set_volume)

    def __load_song(self, song):
        self.bin = gst.element_factory_make('playbin', 'player')
        from urllib import pathname2url as tourl
        self.bin.set_property('uri', "file://" + tourl(song["~filename"]))
        self.__length = song["~#length"] * 1000
        if self.__paused: self.bin.set_state(gst.STATE_PAUSED)
        else: self.bin.set_state(gst.STATE_PLAYING)

    def seek(self, pos):
        if self.bin:
            pos = max(0, int(pos))
            if pos >= self.__length:
                self.paused = True
                pos = self.__length

            state = self.bin.get_state()
            self.bin.set_state(gst.STATE_PAUSED)
            ms *= gst.MSECOND
            event = gst.event_new_seek(gst.FORMAT_TIME|gst.SEEK_METHOD_SET, ms)
            self.bin.send_event(event)
            self.bin.set_state(state)

            self.info.time = (pos, self.__length)
            self.info.seek(self.__song, pos)

    def remove(self, song):
        if self.__song is song: self.__end(False)

    def __get_song(self):
        if self.bin is not None:
            self.bin.set_state(gst.STATE_NULL)
        song = self.__source.current
        if song is None:
            self.__update_time()
            return None

        config.set("memory", "song", song["~filename"])
        try: self.__load_song(song)
        except Exception, err:
            sys.stderr.write(str(err) + "\n")
            player = None
            self.paused = True
            self.info.missing(song)
            self.info.time = (0, 1)
        else:
            self.info.song_started(song)
        self.__update_time()
        return song

    def __end(self, stopped=True):
        if self.bin is not None:
            self.bin.set_state(gst.STATE_NULL)
            self.bin = None
            self.info.song_ended(self.__song, stopped)
            self.__song = None

        if not stopped: self.__do()

    def __do(self):
        self.__song = self.__get_song()
        if self.bin is not None:
            self.bin.connect_object('eos', self.__end, False)
            
    def reset(self):
        self.__source.reset()

    def next(self):
        self.__end()
        self.paused = False
        self.__source.next()
        self.__do()

    def quitting(self):
        self.quit = True
        self.paused = False
        self.__end()

    def previous(self):
        self.paused = False
        self.__source.previous()
        self.__end()
        self.__do()

    def go_to(self, song):
        self.__source.go_to(song)
        self.__end()
        self.__do()

global device, playlist
playlist = None

def init(devid):
    if ":" in devid:
        name, args = devid.split(":")[0], devid.split(":")[1:]
    else: name, args = devid, []
    name = "gst"

    global device, playlist
    playlist = PlaylistPlayer(*args)
    device = playlist
    return playlist
