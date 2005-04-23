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
from formats import MusicPlayer
from library import library

BUFFER_SIZE = 2**8

class OSSAudioDevice(object):
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

class AOAudioDevice(object):
    def __init__(self, dev):
        import ao
        try:
            self.__dev = ao.AudioDevice(dev, rate=44100, channels=2, bits=16)
        except ao.aoError: raise IOError
        self.volume = 1.0
        self.set_info(44100, 2)

    def set_info(self, rate, channels):
         self.__rate = rate
         self.__ratestate = None
         if rate != 44100: self.__rate_conv = audioop.ratecv
         else: self.__rate_conv = lambda *args: (args[0], None)
         if channels != 2: self.__chan_conv = audioop.tostereo
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
        self.__shuffle = False
        self.__player = None
        self.__song = None
        self.__sort = cmp
        self.__lock = threading.Lock()
        self.filter = None
        self.repeat = False
        self.paused = True
        self.quit = False
        self.sort_by("artist")

    def __iter__(self): return iter(self.__orig_playlist)

    def __set_paused(self, paused):
        self.__paused = paused
        try: self.info.set_paused(paused)
        except AttributeError: pass

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

    def refilter(self):
        self.set_playlist(filter(self.filter, library.values()))

    def playlist_from_filters(self, *filters):
        if not filter(None, filters): self.filter = None
        else:
            def parse(text):
                try: return parser.parse(text)
                except parser.error: return None
            filters = filter(None, map(parse, filters))
            if not filters: return False
            elif len(filters) == 1: self.filter = filters[0].search
            else: self.filter = match.Inter(filters).search
        self.refilter()
        return True

    def remove(self, song):
        self.__lock.acquire()
        try: self.__orig_playlist.remove(song)
        except ValueError: pass
        try: self.__playlist.remove(song)
        except ValueError: pass
        try: self.__played.remove(song)
        except ValueError: pass
        self.__lock.release()

    def __get_song(self):
        self.__lock.acquire()
        song = self.__playlist.pop(0)
        fn = song['~filename']
        config.set("memory", "song", fn)
        if self.shuffle: random.shuffle(self.__playlist)
        try: player = MusicPlayer(self.__output, song)
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

    def play(self, info):
        self.info = info
        self.__lock.acquire()
        last_song = config.get("memory", "song")
        if last_song in library:
            song = library[last_song]
            if song in self.__playlist:
                self.go_to(song, lock=False)
        self.__lock.release()

        while not self.quit:
            while self.__playlist and not self.quit:
                self.__song, self.__player = self.__get_song()
                if not self.__player: continue
                while self.paused: time.sleep(0.05)
                for t in self.__player:
                    self.info.time = (t, self.__player.length)
                    while self.paused and not self.quit:
                        time.sleep(0.05)
                    if self.quit: break
                if not self.__player.stopped:
                    self.__song["~#lastplayed"] = int(time.time())
                    self.__song["~#playcount"] += 1
                self.info.song_ended(self.__song, self.__player.stopped)

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

    def sort_by(self, header, reverse = False):
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
        self.set_playlist(pl, lock = False)
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
            self.__playlist.remove(song)
            self.__playlist.insert(0, song)
            if self.__player: self.__player.end()
        if lock: self.__lock.release()

def OSSProxy(*args):
    print "W: Unable to open the requested audio device."
    print "W: Falling back to Open Sound System support."
    return OSSAudioDevice()

supported = {}
outputs = { 'oss': OSSAudioDevice }

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
