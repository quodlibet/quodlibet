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
import time
import stat
import os

BUFFER_SIZE = 2**8

class AudioPlayer(object):
    def __init__(self):
        self.stopped = False

    def pause(self): pass
    def unpause(self): pass

    def end(self):
        self.stopped = True

class MP3Player(AudioPlayer):
    def __init__(self, dev, song):
        import mad
        filename = song['=filename']
        AudioPlayer.__init__(self)
        self.dev = dev
        self.audio = mad.MadFile(filename)
        self.dev.set_info(self.audio.samplerate(), 2)
        self.length = self.audio.total_time()

    def __iter__(self): return self

    def seek(self, ms):
        self.audio.seek_time(int(ms))

    def next(self):
        if self.stopped: raise StopIteration
        buff = self.audio.read(BUFFER_SIZE)
        if buff is None: raise StopIteration
        self.dev.play(buff)
        return self.audio.current_time()

class FLACPlayer(AudioPlayer):
    def __init__(self, dev, song):
        AudioPlayer.__init__(self)
        filename = song['=filename']
        import flac.decoder, flac.metadata
        self.STREAMINFO = flac.metadata.STREAMINFO
        self.EOF = flac.decoder.FLAC__FILE_DECODER_END_OF_FILE
        self.OK = flac.decoder.FLAC__FILE_DECODER_OK
        self.dev = dev
        self.dec = flac.decoder.FileDecoder()
        self.dec.set_md5_checking(False);
        self.dec.set_filename(filename)
        self.dec.set_metadata_respond_all()
        self.dec.set_write_callback(self._player)
        self.dec.set_metadata_callback(self._grab_stream_info)
        self.dec.set_error_callback(lambda *args: None)
        self.dec.init()
        self.dec.process_until_end_of_metadata()
        self._size = os.stat(filename)[stat.ST_SIZE]

    def _grab_stream_info(self, dec, block):
        if block.type == self.STREAMINFO:
            streaminfo = block.data.stream_info
            self._samples = streaminfo.total_samples
            self._srate = streaminfo.sample_rate / 100
            self.length = (self._samples * 10) / self._srate
            self._bps = streaminfo.bits_per_sample

    def _player(self, dec, buff, size):
        device.play(buff)
        return self.OK

    def next(self):
        if self.stopped:
            self.dec.finish()
            raise StopIteration
        if self.dec.get_state() == self.EOF:
            self.dec.finish()
            raise StopIteration
        if not self.dec.process_single():
            self.dec.finish()
            raise StopIteration
        pos = self.dec.get_decode_position()
        return int(self.length * (float(pos) / self._size))

    def __iter__(self):
        return self

    def seek(self, ms): pass
        #samp = int((float(ms) / self.length) * self._samples)
        #self.dec.seek_absolute(samp)

class OggPlayer(AudioPlayer):
    def __init__(self, dev, song):
        AudioPlayer.__init__(self)
        filename = song['=filename']
        import ogg.vorbis
        self.error = ogg.vorbis.VorbisError
        self.dev = dev
        self.audio = ogg.vorbis.VorbisFile(filename)
        rate = self.audio.info().rate
        channels = self.audio.info().channels
        self.replay_gain(song)
        self.dev.set_info(rate, channels)
        self.length = int(self.audio.time_total(-1) * 1000)

    def __iter__(self): return self

    def replay_gain(self, song):
        gain = config.getint("settings", "gain")
        try:
            if gain == 0: raise ValueError
            elif gain == 2 and "replaygain_album_gain" in song:
                db = float(song["replaygain_album_gain"].split()[0])
                peak = float(song["replaygain_album_peak"])
            elif gain > 0 and "replaygain_track_gain" in song:
                db = float(song["replaygain_track_gain"].split()[0])
                peak = float(song["replaygain_track_peak"])
            else: raise ValueError
            self.scale = 10.**(db / 20)
            
            if self.scale * peak > 1: self.scale = 1.0 / peak # don't clip
            if self.scale > 15: self.scale = 15 # probably messed up...
        except (KeyError, ValueError):
            self.scale = 1

    def seek(self, ms):
        self.audio.time_seek(ms / 1000.0)

    def next(self):
        if self.stopped: raise StopIteration
        try: (buff, bytes, bit) = self.audio.read(BUFFER_SIZE)
        except self.error: pass
        else:
            if bytes == 0: raise StopIteration
            if self.scale != 1:
                buff = audioop.mul(buff, 2, self.scale)
                bytes = len(buff)
            self.dev.play(buff)
        return int(self.audio.time_tell() * 1000)

class ModPlayer(AudioPlayer):
    def __init__(self, dev, song):
        AudioPlayer.__init__(self)
        import modplug
        self.audio = modplug.ModFile(song["=filename"])
        self.length = self.audio.length
        self.pos = 0
        self.dev = dev
        self.dev.set_info(44100, 2)

    def __iter__(self): return self

    def seek(self, ms):
        self.audio.seek(ms)
        self.pos = ms

    def next(self):
        if self.stopped: raise StopIteration
        else:
            s = self.audio.read(BUFFER_SIZE)
            if s:
                self.pos += float(len(s)) / 176.400 # 2 / 2 / 44100
                self.dev.play(s)
            else: self.stopped = True
        return self.pos

def FilePlayer(dev, song):
    for ext in supported.keys():
        if song["=filename"].lower().endswith(ext):
            return supported[ext](dev, song)
    else: raise RuntimeError("Unknown file format: %s" % song["=filename"])

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
        self.rate = 44100
        self.ratestate = None
        try: self.dev = ao.AudioDevice(device, rate = 44100,
                                       channels = 2, bits = 16)
        except ao.aoError: raise IOError
        self.volume = 1.0

    def set_info(self, rate, channels):
         if rate != 44100:
             self.ratestate = None
             self.rate = rate
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
        self._paused = True
        self.song = None
        self.quit = False
        self.sort = cmp
        self.filter = None
        self.lock = threading.Lock()

        fn = config.get("memory", "song")
        if fn and fn in library:
            self.playlist.insert(0, library[fn])

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
        self.lock.acquire()
        last_song =  config.get("memory", "song")
        if last_song in library:
            song = library[last_song]
            if song in self.playlist: self.go_to(song, lock = False)
            else: self.playlist.insert(0, song)
        self.lock.release()

        dump_fn = os.path.join(os.path.expanduser("~"), ".quodlibet", "current")
        while not self.quit:
            while self.playlist and not self.quit:
                self.lock.acquire()
                self.song = self.playlist.pop(0)
                fn = self.song['=filename']
                config.set("memory", "song", fn)
                f = file(dump_fn, "w")
                f.write(self.song.to_dump())
                f.close()
                if self.shuffle: random.shuffle(self.playlist)
                try: self.player = FilePlayer(self.output, self.song)
                except None:
                    self.paused = True
                    self.info.missing_song(self.song)
                    self.played.append(self.song)
                    self.lock.release()
                else:
                    self.info.set_song(self.song, self.player)
                    self.played.append(self.song)
                    self.lock.release()
                    while self.paused: time.sleep(0.1)
                    for t in self.player:
                        self.info.set_time(t, self.player.length)
                        while self.paused and not self.quit:
                            time.sleep(0.1)
                        if self.quit: break
                    if not self.player.stopped:
                        self.song["=lastplayed"] = int(time.time())
                        self.song["=playcount"] += 1

            if self.repeat:
                self.playlist = self.orig_playlist[:]
                if self.shuffle and len(self.played) > 500:
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
        if self.player: self.player.end()
        self.paused = False
        self.lock.release()

    def quitting(self):
        self.lock.acquire()
        dump_fn = os.path.join(os.path.expanduser("~"), ".quodlibet", "current")
        try: os.unlink(dump_fn)
        except OSError: pass
        self.quit = True
        self.paused = False
        if self.player: self.player.end()
        self.lock.release()

    def previous(self):
        self.lock.acquire()
        self.paused = False
        if len(self.played) >= 2 and self.player:
            if self.player: self.player.end()
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
    if util.check_ogg(): supported[".ogg"] = OggPlayer
    if util.check_mp3(): supported[".mp3"] = MP3Player
    if util.check_flac(): supported[".flac"] = FLACPlayer

    if util.check_mod():
        for fmt in ["669", "amf", "dsm", "gdm", "imf", "it",
                    "med", "mod", "mtm", "s3m", "stm", "stx",
                    "ult", "uni", "apun", "xm"]:
            supported["." + fmt] = ModPlayer
            supported["." + fmt + ".gz"] = ModPlayer
            supported["." + fmt + ".bz2"] = ModPlayer


    try: import ao
    except ImportError: outputs['ao'] = OSSProxy
    else: outputs['ao'] = AOAudioDevice

    if ":" in devid:
        name, args = devid.split(":")[0], devid.split(":")[1:]
    else: name, args = devid, []

    global device, playlist
    device = outputs.get(name, OSSAudioDevice)(*args)
    playlist = PlaylistPlayer(output = device)
