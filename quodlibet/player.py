# Copyright 2004 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import time
import threading
import random
import config
from library import library
import parser
import audioop
import util
import stat
import os
import formats
import const
import match

BUFFER_SIZE = 2**8

class OSSAudioDevice(object):
    def __init__(self):
        import ossaudiodev
        self.dev = ossaudiodev.open("w")
        self.dev.setfmt(ossaudiodev.AFMT_S16_LE)
        self._channels = self.dev.channels(2)
        self._rate = self.dev.speed(44100)
        self.volume = 1.0
        self.dev.nonblock()

    def play(self, buf):
        if self.volume != 1.0: buf = audioop.mul(buf, 2, self.volume)
        self.dev.writeall(buf)

    def set_info(self, rate, channels):
        if rate != self._rate or channels != self._channels:
            import ossaudiodev
            self.dev.close()
            self.dev = ossaudiodev.open("w")
            self.dev.setfmt(ossaudiodev.AFMT_S16_LE)
            self._channels = self.dev.channels(channels)
            self._rate = self.dev.speed(rate)
            self.dev.nonblock()

class AOAudioDevice(object):
    def __init__(self, device):
        import ao
        try: self.dev = ao.AudioDevice(device, rate = 44100,
                                       channels = 2, bits = 16)
        except ao.aoError: raise IOError
        self.volume = 1.0
        self.set_info(44100, 2)

    def set_info(self, rate, channels):
         self.rate = rate
         self.ratestate = None
         if rate != 44100:
             self.rate_conv = audioop.ratecv
         else: self.rate_conv = lambda *args: (args[0], None)
         if channels != 2: self.chan_conv = audioop.tostereo
         else: self.chan_conv = lambda *args: args[0]

    def play(self, buf):
        buf = self.chan_conv(buf, 2, 1, 1)
        if self.volume != 1.0: buf = audioop.mul(buf, 2, self.volume)
        buf, self.ratestate = self.rate_conv(buf, 2, 2, self.rate,
                                             44100, self.ratestate)
        self.dev.play(buf, len(buf))

class PlaylistPlayer(object):
    def __init__(self, output, playlist = []):
        self.output = output
        self.playlist = playlist
        self.played = []
        self.orig_playlist = playlist[:]
        self._shuffle = False
        self.repeat = False
        self.player = None
        self.paused = True
        self.song = None
        self.quit = False
        self.sort = cmp
        self.filter = None
        self.lock = threading.Lock()
        fn = config.get("memory", "song")
        if fn and fn in library:
            self.playlist.insert(0, library[fn])
        self.sort_by("artist")

    def __iter__(self): return iter(self.orig_playlist)

    def set_paused(self, paused):
        self._paused = paused
        try: self.info.set_paused(paused)
        except AttributeError: pass
        if paused:
            try: file(const.PAUSED, "w").close()
            except: pass
        else:
            try: os.unlink(const.PAUSED)
            except: pass

    def get_paused(self): return self._paused

    paused = property(get_paused, set_paused)

    def seek(self, pos):
        self.lock.acquire()
        if self.player:
            pos = max(0, int(pos))
            if pos >= self.player.length:
                self.paused = True
                pos = self.player.length

            self.info.set_time(pos, self.player.length)
            self.player.seek(pos)
        self.lock.release()

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
        self.lock.acquire()
        self.orig_playlist.remove(song)
        try: self.playlist.remove(song)
        except ValueError: pass
        try: self.played.remove(song)
        except ValueError: pass
        self.lock.release()

    def play(self, info):
        self.info = info
        self.lock.acquire()
        last_song = config.get("memory", "song")
        if last_song in library:
            song = library[last_song]
            if song in self.playlist: self.go_to(song, lock = False)
            else: self.playlist.insert(0, song)
        self.lock.release()

        while not self.quit:
            while self.playlist and not self.quit:
                self.lock.acquire()
                self.song = self.playlist.pop(0)
                fn = self.song['~filename']
                config.set("memory", "song", fn)
                try: # potentially, permissions error, out of disk space
                    f = file(const.CURRENT, "w")
                    f.write(self.song.to_dump())
                    f.close()
                except (IOError, OSError): pass
                if self.shuffle: random.shuffle(self.playlist)
                try: self.player = formats.MusicPlayer(self.output, self.song)
                except:
                    self.paused = True
                    self.info.missing_song(self.song)
                    self.lock.release()
                else:
                    self.info.start_song(self.song)
                    self.played.append(self.song)
                    self.lock.release()
                    while self.paused: time.sleep(0.05)
                    for t in self.player:
                        self.info.set_time(t, self.player.length)
                        while self.paused and not self.quit:
                            time.sleep(0.05)
                        if self.quit: break
                    if not self.player.stopped:
                        self.song["~#lastplayed"] = int(time.time())
                        self.song["~#playcount"] += 1

            while self.paused and not self.quit:
                time.sleep(0.05)

            if self.repeat:
                self.playlist = self.orig_playlist[:]
                if self.shuffle and len(self.played) > 500:
                    del(self.played[500:])
            else:
                if self.song or self.player:
                    self.lock.acquire()
                    self.song = self.player = None
                    self.info.start_song(self.song)
                    self.paused = True
                    self.lock.release()
                    try: os.unlink(const.CURRENT)
                    except OSError: pass
                time.sleep(0.1)

    def reset(self):
        self.lock.acquire()
        self.playlist = self.orig_playlist[:]
        self.paused = False
        self.lock.release()

    def sort_by(self, header, reverse = False):
        self.lock.acquire()
        pl = self.orig_playlist[:]
        if header == "~#track": header = "album"
        elif header == "~#disc": header = "album"
        elif header == "~length": header = "~#length"
        if reverse:
            f = lambda b, a: (cmp(a(header), b(header)) or cmp(a, b))
        else:
            f = lambda a, b: (cmp(a(header), b(header)) or cmp(a, b))
        self.sort = f
        self.set_playlist(pl, lock = False)
        self.lock.release()

    def get_playlist(self):
        return self.orig_playlist

    def set_playlist(self, pl, lock = True):
        if lock: self.lock.acquire()
        pl.sort(self.sort)
        self.played = []
        self.playlist = pl
        self.orig_playlist = pl[:]
        if self.song and self.song in playlist and not self.shuffle:
            i = self.orig_playlist.index(self.song) + 1
            self.played = self.orig_playlist[:i]
            self.playlist = self.orig_playlist[i:]
        elif self.shuffle:
            random.shuffle(self.playlist)
        if lock: self.lock.release()

    def set_shuffle(self, shuffle):
        self.lock.acquire()
        self._shuffle = shuffle
        if shuffle:
            
            if self.song and self.song in self.orig_playlist:
                self.played = [self.song]
            else: self.played = []
            self.playlist = self.orig_playlist[:]
            random.shuffle(self.playlist)
        else:
            if self.song and self.song in self.orig_playlist:
                i = self.orig_playlist.index(self.song) + 1
                self.played = self.orig_playlist[:i]
                self.playlist = self.orig_playlist[i:]
        self.lock.release()

    def get_shuffle(self): return self._shuffle

    shuffle = property(get_shuffle, set_shuffle)

    def next(self):
        self.lock.acquire()
        if self.player:
            self.player.end()
            self.song["~#skipcount"] = self.song.get("~#skipcount", 0) + 1
        self.paused = False
        self.lock.release()

    def quitting(self):
        self.lock.acquire()
        try: os.unlink(const.CURRENT)
        except OSError: pass
        self.quit = True
        self.paused = False
        if self.player: self.player.end()
        self.lock.release()

    def previous(self):
        self.lock.acquire()
        self.paused = False
        if len(self.played) >= 2 and self.player:
            self.player.end()
            self.song["~#skipcount"] = self.song.get("~#skipcount", 0) + 1
            self.playlist.insert(0, self.played.pop())
            self.playlist.insert(0, self.played.pop())
        elif self.played:
            if self.repeat:
                self.played = self.orig_playlist[:-1]
                self.playlist = [self.orig_playlist[-1]]
            else:
                if self.player: self.player.end()
                self.playlist.insert(0, self.played.pop())
        else: pass
        self.lock.release()

    def go_to(self, song, lock = True):
        if self.song and self.song != song:
            self.song["~#skipcount"] = self.song.get("~#skipcount", 0) + 1
        if lock: self.lock.acquire()
        if not self.shuffle:
            i = self.orig_playlist.index(song)
            self.played = self.orig_playlist[:i]
            self.playlist = self.orig_playlist[i:]
            if self.player: self.player.end()
        else:
            del(self.playlist[:])
            self.playlist.extend(self.orig_playlist)
            self.playlist.remove(song)
            self.playlist.insert(0, song)
            if self.player: self.player.end()
        if lock: self.lock.release()

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
    playlist = PlaylistPlayer(output = device)
