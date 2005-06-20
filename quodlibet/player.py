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
import match
import parser
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
                else: sinkname == "osssink"

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
    def get_volume(self, v): return self.__volume
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

    def __init__(self, dev):
        import ao
        try:
            self.__dev = ao.AudioDevice(dev, rate=44100, channels=2, bits=16)
        except ao.aoError: raise IOError
        self.volume = 1.0
        self.set_info(44100, 2)
        self.name = "ao:" + dev

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
        self.__playlist = playlist
        self.__played = []
        self.__orig_playlist = playlist[:]
        self.__shuffle = 0
        self.__player = None
        self.__song = None
        self.__paused = False
        self.__sort = cmp
        self.__lock = threading.Lock()
        self.repeat = False
        self.paused = True
        self.quit = False
        self.sort_by("artist")

    def __iter__(self): return iter(self.__orig_playlist)

    def __set_paused(self, paused):
        if paused != self.__paused:
            self.__paused = paused
            try: self.info.set_paused(paused)
            except AttributeError: pass
            self.__output.paused = paused

    def __get_paused(self): return self.__paused

    paused = property(__get_paused, __set_paused)

    def seek(self, pos):
        self.__lock.acquire()
        if self.__player:
            pos = max(0, int(pos))
            if pos >= self.__player.length:
                self.paused = True
                pos = self.__player.length

            self.info.time = (pos, self.__player.length)
            self.info.seek(self.__song, pos)
            self.__player.seek(pos)
        self.__lock.release()

    def remove(self, song):
        self.__lock.acquire()
        try: self.__orig_playlist.remove(song)
        except ValueError: pass
        try: self.__playlist.remove(song)
        except ValueError: pass
        try: self.__played.remove(song)
        except ValueError: pass
        if self.__song is song and self.__player: self.__player.end()
        self.__lock.release()

    def __get_song(self):
        self.__lock.acquire()
        if (self.shuffle == 2 and
            (len(self.__playlist) == len(self.__orig_playlist))):
            # Weighted random without songs pending
            plist = self.__orig_playlist
            total_rating = sum([song.get("~#rating", 2) for song in plist])
            choice = random.random() * total_rating
            current = 0.0
            for song in plist:
                current += song.get("~#rating", 2)
                if current >= choice: break
            self.__playlist.insert(0, song)

        song = self.__playlist.pop(0)
        if self.shuffle == 1: random.shuffle(self.__playlist)
        config.set("memory", "song", song["~filename"])
        try: player = self.__output.open(song)
        except Exception, err:
            sys.stderr.write(str(err) + "\n")
            player = None
            self.paused = True
            self.info.missing(song)
        else:
            self.info.song_started(song)
            self.__played.append(song)
        self.__lock.release()
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

    def play(self, info, song):
        self.info = info
        self.__lock.acquire()
        if song and song in self.__playlist: self.go_to(song, lock=False)
        self.__lock.release()

        while not self.quit:
            while self.__playlist and not self.quit:
                self.__song, self.__player = self.__get_song()
                if not self.__player: continue
                if self.__play_internal():
                    if not self.__player.stopped:
                        self.__song["~#lastplayed"] = int(time.time())
                        self.__song["~#playcount"] += 1
                    self.info.song_ended(self.__song, self.__player.stopped)
                else:
                    self.paused = True
                    self.info.missing(self.__song)

            while self.paused and not self.quit:
                time.sleep(0.05)

            if self.repeat: self.reset()
            else:
                if self.__song or self.__player:
                    self.__lock.acquire()
                    self.__song = self.__player = None
                    self.info.song_started(self.__song)
                    self.paused = True
                    self.__lock.release()
            time.sleep(0.1)

    def reset(self):
        self.__lock.acquire()
        self.__playlist = self.__orig_playlist[:]
        if self.shuffle and len(self.__played) > 500:
            del(self.__played[500:])
        self.paused = False
        self.__lock.release()

    def sort_by(self, header, reverse=False):
        self.__lock.acquire()
        pl = self.__orig_playlist[:]
        if header == "~#track": header = "album"
        elif header == "~#disc": header = "album"
        elif header == "~length": header = "~#length"
        if reverse:
            f = lambda b, a: (cmp(a(header), b(header)) or cmp(a, b))
        else:
            f = lambda a, b: (cmp(a(header), b(header)) or cmp(a, b))
        self.__sort = f
        self.set_playlist(pl, lock=False)
        self.__lock.release()

    def get_playlist(self):
        return self.__orig_playlist

    def set_playlist(self, pl, lock=True):
        if lock: self.__lock.acquire()
        pl.sort(self.__sort)
        self.__played = []
        self.__playlist = pl
        self.__orig_playlist = pl[:]
        if self.__song and self.__song in playlist and not self.shuffle:
            i = self.__orig_playlist.index(self.__song) + 1
            self.__played = self.__orig_playlist[:i]
            self.__playlist = self.__orig_playlist[i:]
        elif self.shuffle:
            random.shuffle(self.__playlist)
        if lock: self.__lock.release()

    def __set_shuffle(self, shuffle):
        self.__lock.acquire()
        self.__shuffle = shuffle

        if shuffle:
            if self.__song and self.__song in self.__orig_playlist:
                self.__played = [self.__song]
            else: self.__played = []

            self.__playlist = self.__orig_playlist[:]
            random.shuffle(self.__playlist)
        else:
            if self.__song and self.__song in self.__orig_playlist:
                i = self.__orig_playlist.index(self.__song) + 1
                self.__played = self.__orig_playlist[:i]
                self.__playlist = self.__orig_playlist[i:]
        self.__lock.release()

    def __get_shuffle(self): return self.__shuffle

    shuffle = property(__get_shuffle, __set_shuffle)

    def next(self):
        self.__lock.acquire()
        if self.__player:
            self.__player.end()
            self.__song["~#skipcount"] = self.__song.get("~#skipcount", 0) + 1
        self.paused = False
        self.__lock.release()

    def quitting(self):
        self.__lock.acquire()
        self.quit = True
        self.paused = False
        if self.__player: self.__player.end()
        self.__lock.release()

    def previous(self):
        self.__lock.acquire()
        self.paused = False
        if len(self.__played) >= 2 and self.__player:
            self.__player.end()
            self.__song["~#skipcount"] = self.__song.get("~#skipcount", 0) + 1
            self.__playlist.insert(0, self.__played.pop())
            self.__playlist.insert(0, self.__played.pop())
        elif self.__played:
            if self.repeat:
                self.__played = self.__orig_playlist[:-1]
                self.__playlist = [self.__orig_playlist[-1]]
            else:
                if self.__player: self.__player.end()
                self.__playlist.insert(0, self.__played.pop())
        else: pass
        self.__lock.release()

    def go_to(self, song, lock=True):
        if self.__song and self.__song is not song:
            self.__song["~#skipcount"] = self.__song.get("~#skipcount", 0) + 1
        if lock: self.__lock.acquire()
        if not self.shuffle:
            i = self.__orig_playlist.index(song)
            self.__played = self.__orig_playlist[:i]
            self.__playlist = self.__orig_playlist[i:]
            if self.__player: self.__player.end()
        else:
            del(self.__playlist[:])
            self.__playlist.extend(self.__orig_playlist)
            if self.shuffle == 1: self.__playlist.remove(song)
            self.__playlist.insert(0, song)
            if self.__player: self.__player.end()
        if lock: self.__lock.release()

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
