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
    __paused = False
    song = None
    info = None
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

    def __load_song(self, song):
        st = self.bin.set_state(gst.STATE_NULL)
        if st != gst.STATE_SUCCESS: raise Exception(st)
        self.bin.set_property('uri', song("~uri"))
        self.__length = song["~#length"] * 1000
        if self.__paused: st = self.bin.set_state(gst.STATE_PAUSED)
        else: st = self.bin.set_state(gst.STATE_PLAYING)
        if st != gst.STATE_SUCCESS: raise Exception(st)

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

    def __get_song(self, lock=False):
        song = self.__source.current
        self.song = song
        self.info.song_started(song)
        self.volume = self.__volume
        if song is not None:
            config.set("memory", "song", song["~filename"])
            try: self.__load_song(song)
            except Exception, err:
                import traceback; traceback.print_exc()
                self.error(err, lock)
                return
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
            # Avoids a deadlock if the song ends and the user presses a
            # a button that calls __end at the same time; both threads
            # end up waiting for something inside GSt.
            gobject.idle_add(self.__get_song, True)

    def __tag(self, pipeline, source, tags):
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
                    elif k == "title" and self.song.multisong:
                        proxy[k] = value
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
    if gst.element_make_from_uri(gst.URI_SRC, "file://", ""):
        global playlist
        playlist = PlaylistPlayer(pipeline or "gconf")
        return playlist
    else: raise NoSourceError
