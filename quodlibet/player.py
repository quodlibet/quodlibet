# Copyright 2004 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import ao
import time
import threading
import random
from library import library
import parser
import ossaudiodev # barf
import util
import time
import os

BUFFER_SIZE = 2**12

class AudioPlayer(object):
    def __init__(self):
        self.stopped = False

    def end(self):
        self.stopped = True

class MP3Player(AudioPlayer):
    def __init__(self, dev, filename):
        AudioPlayer.__init__(self)
        self.dev = dev
        self.audio = mad.MadFile(filename)
        self.length = self.audio.total_time()

    def __iter__(self): return self

    def seek(self, ms):
        self.audio.seek_time(int(ms))

    def next(self):
        if self.stopped: raise StopIteration
        buff = self.audio.read(BUFFER_SIZE)
        if buff is None: raise StopIteration
        self.dev.play(buff, len(buff))
        return self.audio.current_time()

class FLACPlayer(AudioPlayer):
    def __init__(self, dev, filename):        
        AudioPlayer.__init__(self)
        self.dev = dev
        self.length = 100 # FIXME
        self.dec = flac.decoder.FileDecoder()
        self.dec.set_md5_checking(False);
        self.dec.set_filename(filename)
        self.dec.set_metadata_ignore_all()
        self.dec.set_write_callback(self._player)
        self.dec.set_metadata_callback(lambda *args: None)
        self.dec.set_error_callback(lambda *args: None)

    def _player(self, dec, buff, size):
        device.play(buff, size)
        return flac.decoder.FLAC__FILE_DECODER_OK

    def next(self):
        if self.stopped: raise StopIteration
        if self.dec.get_state() == flac.decoder.FLAC__FILE_DECODER_END_OF_FILE:
            self.dec.finish()
            raise StopIteration
        if not self.dec.process_single():
            self.dec.finish()
            raise StopIteration
        #return dec.get_decode_position() / 1000
        return 0

    def __iter__(self):
        self.dec.init()
        self.dec.process_until_end_of_metadata()
        return self

    def seek(self, ms):
        pass # FIXME

    def end(self):
        AudioPlayer.end(self)
        self.dec.finish()

class OggPlayer(AudioPlayer):
    def __init__(self, dev, filename):
        AudioPlayer.__init__(self)
        self.dev = dev
        self.audio = ogg.vorbis.VorbisFile(filename)
        self.length = self.audio.time_total(-1) * 1000

    def __iter__(self): return self

    def seek(self, ms):
        self.audio.time_seek(ms / 1000.0)

    def next(self):
        if self.stopped: raise StopIteration
        try: (buff, bytes, bit) = self.audio.read(BUFFER_SIZE)
        except ogg.vorbis.VorbisError: pass
        else:
            if bytes == 0: raise StopIteration
            self.dev.play(buff, bytes)
        return self.audio.time_tell() * 1000

def FilePlayer(dev, filename):
    for ext in supported.keys():
        if filename.lower().endswith(ext):
            return supported[ext](dev, filename)
    else: raise RuntimeError("Unknown file format: %s" % filename)

class DummyOutput(object):
    def play(self, buf): time.sleep(len(buf) / 1000000.0)
    def set_volume(self, v): pass
    def get_volume(self): pass
    volume = property(get_volume, set_volume)

class OutputDevice(object):
    def __init__(self):
        self.mixer = ossaudiodev.openmixer()
        self.dev = ao.AudioDevice(ao.driver_id('oss'))
        self.play = self.dev.play

    def get_volume(self):
        return self.mixer.get(ossaudiodev.SOUND_MIXER_PCM)[0]

    def set_volume(self, vol):
        return self.mixer.set(ossaudiodev.SOUND_MIXER_PCM, (vol, vol))

    volume = property(get_volume, set_volume)

class PlaylistPlayer(object):
    def __init__(self, output = None, playlist = []):
        if output: self.output = output
        else: self.output = DummyOutput()
        self.playlist = playlist
        self.played = []
        self.orig_playlist = playlist[:]
        self.shuffle = False
        self.repeat = False
        self.player = None
        self._paused = True
        self.song = None
        self.quit = False
        self.sort = cmp
        self.filter = None
        self.lock = threading.Lock()

    def __iter__(self): return iter(self.orig_playlist)

    def set_paused(self, paused):
        self._paused = paused
        self.info.set_paused(paused)

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

    def playlist_from_filter(self, text):
        if text == "": self.filter = None
        else:
            try: q = parser.parse(text)
            except parser.error: return False
            else: self.filter = q.search
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
        dump_fn = os.path.join(os.environ["HOME"], ".quodlibet", "current")
        while not self.quit:
            while self.playlist:
                self.lock.acquire()
                self.song = self.playlist.pop(0)
                fn = self.song['filename']
                if self.shuffle: random.shuffle(self.playlist)
                f = file(dump_fn, "w")
                f.write(self.song.to_dump())
                f.close()
                try: self.player = FilePlayer(self.output, fn)
                except:
                    self.paused = True
                    self.info.missing_song(self.song)
                    self.played.append(self.song)
                    self.lock.release()
                else:
                    self.info.set_song(self.song, self.player)
                    self.played.append(self.song)
                    self.lock.release()
                    for t in self.player:
                        self.info.set_time(t, self.player.length)
                        while self.paused and not self.quit:
                            time.sleep(0.1)
                    if not self.player.stopped:
                        self.song["=lastplayed"] = int(time.time())
                        self.song["=playcount"] += 1

            if self.repeat:
                self.playlist = self.orig_playlist[:]
                if len(self.played) > 500:
                    del(self.played[500:])
            else:
                if self.song or self.player:
                    self.lock.acquire()
                    self.song = self.player = None
                    self.info.set_song(self.song, self.player)
                    self.paused = True
                    self.lock.release()
                    try: os.unlink(dump_fn)
                    except OSError: pass
                time.sleep(0.1)

    def sort_by(self, header, reverse = False):
        self.lock.acquire()
        pl = self.orig_playlist[:]
        if header == "=#": header = "album"
        if reverse:
            f = lambda b, a: (cmp(a.get(header), b.get(header)) or cmp(a, b))
        else:
            f = lambda a, b: (cmp(a.get(header), b.get(header)) or cmp(a, b))
        self.sort = f
        pl.sort(self.sort)
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
        if lock: self.lock.release()

    def next(self):
        self.lock.acquire()
        if self.player: self.player.end()
        self.paused = False
        self.lock.release()

    def quitting(self):
        self.lock.acquire()
        dump_fn = os.path.join(os.environ["HOME"], ".quodlibet", "current")
        try: os.unlink(dump_fn)
        except OSError: pass
        self.quit = True
        self.paused = False
        if self.player: self.player.end()
        self.set_playlist([], lock = False)
        self.lock.release()

    def previous(self):
        self.lock.acquire()
        self.paused = False
        if len(self.played) >= 2:
            if self.player: self.player.end()
            self.playlist.insert(0, self.played.pop())
            self.playlist.insert(0, self.played.pop())
        elif self.player and self.played:
            if self.repeat:
                self.played = self.orig_playlist[:-1]
                self.playlist = [self.orig_playlist[-1]]
            else:
                if self.player: self.player.end()
                self.playlist.insert(0, self.played.pop())
        else: pass
        self.lock.release()

    def go_to(self, song):
        self.lock.acquire()
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
        self.lock.release()

supported = {}

if util.check_ogg():
    import ogg.vorbis
    supported[".ogg"] = OggPlayer

if util.check_mp3():
    import mad
    supported[".mp3"] = MP3Player

if util.check_flac():
    import flac.decoder
    supported[".flac"] = FLACPlayer

device = OutputDevice()
playlist = PlaylistPlayer(output = device)
