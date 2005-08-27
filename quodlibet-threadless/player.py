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
import random
import config
import audioop

class OSSAudioDevice(object):
    from formats import MusicPlayer as open

    name = "oss"

    def __init__(self):
        import ossaudiodev
        self.__dev = ossaudiodev.open("w")
        self.__dev.setfmt(ossaudiodev.AFMT_S16_LE)
        self.__channels = self.__dev.channels(2)
        self.__rate = self.__dev.speed(44100)
        self.volume = 1.0
        self.__dev.nonblock()

    def play(self, buf):
        if self.volume != 1.0: buf = audioop.mul(buf, 2, self.volume)
        self.__dev.writeall(buf)

    def set_info(self, rate, channels):
        if rate != self.__rate or channels != self.__channels:
            import ossaudiodev
            self.__dev.close()
            self.__dev = ossaudiodev.open("w")
            self.__dev.setfmt(ossaudiodev.AFMT_S16_LE)
            self.__channels = self.__dev.channels(channels)
            self.__rate = self.__dev.speed(rate)
            self.__dev.nonblock()

class GStreamerDevice(object):
    player = None
    __volume = 1.0
    __paused = True
    from formats.audio import AudioPlayer

    class Player(AudioPlayer):
        def __init__(self, sink, vol, song):
            super(self.__class__, self).__init__()
            bin = self.bin = gst.Thread()
            source = gst.element_factory_make('filesrc', 'src')
            source.set_property('location', song["~filename"])
            os.path.getsize(song["~filename"]) # make sure it exists
            decoder = gst.element_factory_make('spider', 'decoder')
            volume = gst.element_factory_make('volume', 'volume')
            sink = gst.element_factory_make(sink, 'sink')
            bin.add_many(source, decoder, volume, sink)
            gst.element_link_many(source, decoder, volume)

            self.replay_gain(song)
            if self.scale != 1:
                rg = gst.element_factory_make('volume', 'replaygain')
                rg.set_property('volume', self.scale)
                bin.add(rg)
                gst.element_link_many(volume, rg, sink)
            else: volume.link(sink)

            self.position = 0.0
            self.set_state = bin.set_state
            self.get_state = bin.get_state
            self.source = source
            self.sink = sink
            self.volume = volume
            bin.set_state(gst.STATE_READY)
            self.length = song["~#length"] * 1000
            bin.connect_object('eos', bin.set_state, gst.STATE_NULL)
            volume.set_property('volume', vol)

            import gobject; self.idle_add = gobject.idle_add

        def __iter__(self):
            return self

        def __nonzero__(self):
            return (self.bin.get_state() != gst.STATE_NULL)

        def seek(self, ms):
            state = self.bin.get_state()
            self.bin.set_state(gst.STATE_PAUSED)
            ms *= gst.MSECOND
            event = gst.event_new_seek(gst.FORMAT_TIME|gst.SEEK_METHOD_SET, ms)
            self.volume.send_event(event)
            self.bin.set_state(state)

        def next(self):
            if self.bin.get_state() < gst.STATE_READY:
                raise StopIteration
            else:
                time.sleep(0.2)
                position = self.sink.query(
                    gst.QUERY_POSITION, gst.FORMAT_TIME)
                position /= gst.MSECOND
                return max(0, position)

        def end(self):
            self.set_state(gst.STATE_NULL)
            self.set_state = lambda *args: 0 # prevent unpausing
            self.stopped = True

    def __init__(self, sinkname="gconf"):
        os.environ['PYGTK_USE_GIL_STATE_API'] = '' # from jdahlin
        gst.use_threads(True)
        if sinkname == "gconf":
            try: import gconf
            except ImportError: sinkname = "osssink"
            else:
                c = gconf.client_get_default()
                val = c.get("/system/gstreamer/0.8/default/audiosink")
                if val.type == gconf.VALUE_STRING: sinkname = val.get_string()
                else: sinkname = "osssink"

        if gst.element_factory_make(sinkname): self.sinkname = sinkname
        else: self.sinkname = "osssink"

        self.name = "gst:" + self.sinkname

    def open(self, *args):
        if self.player: state = gst.STATE_PLAYING
        elif self.__paused: state = gst.STATE_PAUSED
        else: state = gst.STATE_PLAYING
        self.player = None
        self.player = self.Player(self.sinkname, self.__volume, *args)
        self.player.set_state(state)
        return self.player

    def set_volume(self, v):
        self.__volume = v
        if self.player: self.player.volume.set_property('volume', v)
    def get_volume(self): return self.__volume
    volume = property(get_volume, set_volume)

    def set_paused(self, p):
        if self.player:
            if p: self.player.set_state(gst.STATE_PAUSED)
            else: self.player.set_state(gst.STATE_PLAYING)
        self.__paused = p
    def get_paused(self):
        if self.player is None: return False
        else: return self.player.get_state() == gst.STATE_PAUSED
    paused = property(get_paused, set_paused)

class AOAudioDevice(object):
    from formats import MusicPlayer as open

    def __init__(self, driver, *device):
        import ao
        options = {}
        if device:
            device = ":".join(device)
            if driver == "oss": options = {"dsp": device}
            elif driver == "esd": options = {"host": device}
            elif driver in ["alsa09", "sun", "aixs"]:
                options = {"dev": device}
            self.name = ":".join(["ao", driver, device])
        else: self.name = ":".join(["ao", driver])

        try: self.__dev = ao.AudioDevice(
            driver, bits=16, rate=44100, channels=2, options=options)
        except ao.aoError: raise IOError
        self.volume = 1.0
        self.set_info(44100, 2)

    def set_info(self, rate, channels):
         self.__rate = rate
         self.__ratestate = None
         if rate != 44100: self.__rate_conv = audioop.ratecv
         else: self.__rate_conv = lambda *args: (args[0], None)
         if channels == 1: self.__chan_conv = audioop.tostereo
         else: self.__chan_conv = lambda *args: args[0]

    def play(self, buf):
        buf = self.__chan_conv(buf, 2, 1, 1)
        if self.volume != 1.0: buf = audioop.mul(buf, 2, self.volume)
        buf, self.__ratestate = self.__rate_conv(
            buf, 2, 2, self.__rate, 44100, self.__ratestate)
        self.__dev.play(buf, len(buf))

class PlaylistPlayer(object):
    def __init__(self, output, playlist=[]):
        self.__output = output
        self.__player = None
        self.__song = None
        self.__paused = False
        self.paused = True
        self.quit = False

    def __iter__(self): return iter(self.__source)

    def __set_paused(self, paused):
        if paused != self.__paused:
            self.__paused = paused
            try: self.info.set_paused(paused)
            except AttributeError: pass
            self.__output.paused = paused

    def __get_paused(self): return self.__paused

    paused = property(__get_paused, __set_paused)

    def seek(self, pos):
        if self.__player:
            pos = max(0, int(pos))
            if pos >= self.__player.length:
                self.paused = True
                pos = self.__player.length

            self.info.time = (pos, self.__player.length)
            self.info.seek(self.__song, pos)
            self.__player.seek(pos)

    def remove(self, song):
        if self.__song is song and self.__player: self.__player.end()

    def __get_song(self):
        song = self.__source.current
        config.set("memory", "song", song["~filename"])
        try: player = self.__output.open(song)
        except Exception, err:
            sys.stderr.write(str(err) + "\n")
            player = None
            self.paused = True
            self.info.missing(song)
        else:
            self.info.song_started(song)
        return song, player

    def __play_internal(self):
        while self.paused: time.sleep(0.05)
        try:
            for t in self.__player:
                self.info.time = (t, self.__player.length)
                while self.paused and not self.quit:
                    time.sleep(0.05)
                if self.quit: break
        except Exception, err:
            sys.stderr.write(str(err) + "\n")
            return False
        else:
            # We might have stopped because the file is gone/corrupt.
            return self.__song.exists()

    def play(self, info, source, song):
        self.info = info
        self.__source = source
        self.go_to(song)

        while not self.quit:
            while self.__source.current and not self.quit:
                self.__song, self.__player = self.__get_song()
                if not self.__player: continue
                if self.__play_internal():
                    if not self.__player.stopped: self.__source.next()
                    self.info.song_ended(self.__song, self.__player.stopped)
                else:
                    self.paused = True
                    self.info.missing(self.__song)

            while self.paused and not self.quit:
                time.sleep(0.05)

            else:
                if self.__song or self.__player:
                    self.__song = self.__player = None
                    self.info.song_started(self.__song)
                    self.paused = True
            time.sleep(0.1)

    def reset(self):
        self.__source.reset()

    def get_playlist(self):
        return self.__source.get()

    def next(self):
        if self.__player: self.__player.end()
        self.paused = False
        self.__source.next()

    def quitting(self):
        self.quit = True
        self.paused = False
        if self.__player:
            self.__player.end()
            self.__player.stopped = False

    def previous(self):
        self.paused = False
        self.__source.previous()
        if self.__player: self.__player.end()

    def go_to(self, song):
        self.__source.go_to(song)
        if self.__player: self.__player.end()

def OSSProxy(*args):
    print "W: Unable to open the requested audio device."
    print "W: Falling back to Open Sound System support."
    return OSSAudioDevice()

supported = {}
outputs = { 'oss': OSSAudioDevice }

try: import gst.play
except ImportError: pass
else: outputs["gst"] = GStreamerDevice

global device, playlist
device = None
playlist = None

def init(devid):
    try: import ao
    except ImportError: outputs['ao'] = OSSProxy
    else: outputs['ao'] = AOAudioDevice

    if ":" in devid:
        name, args = devid.split(":")[0], devid.split(":")[1:]
    else: name, args = devid, []

    global device, playlist
    try: device = outputs.get(name, OSSProxy)(*args)
    except: device = OSSProxy(*args)
    playlist = PlaylistPlayer(output=device)
    return playlist
