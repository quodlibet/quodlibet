import mad
import ao
import ogg.vorbis
import time
from library import library
from parser import QueryParser, QueryLexer
import ossaudiodev # barf

BUFFER_SIZE = 2**8

# Playlist management:
# There are three objects involved in the player; the first is the
# currently playing song; the second is the current playlist (which
# may include the current song, or may not); the third is the list of
# songs remaining to play in the current playlist.
#
# There are two state toggles, repeat and shuffle.
#
# There are four possible actions the user takes:
# 1. Pause (or resume) the current song.
# 2. Change the currently playing song.
# 3. Change the current playlist.
# 4. Go to the next song.
# 5. Go to the previous song.

times = [0, 0]

class AudioPlayer(object):
    def __init__(self):
        self.stopped = False

    # This is the worst function ever.
    def seek(self, *args): self.seek(*args)

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
        (buff, bytes, bit) = self.audio.read(BUFFER_SIZE)
        if bytes == 0: raise StopIteration
        self.dev.play(buff, bytes)
        return self.audio.time_tell() * 1000

def FilePlayer(dev, filename):
    kind = filename.split(".")[-1].lower()
    return { "ogg": OggPlayer,
             "mp3": MP3Player }[kind](dev, filename)

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
        self.shuffle = True
        self.repeat = True
        self.paused = True
        self.song = None

    def seek(self, pos):
        if self.player: self.player.seek(pos)

    def play(self, info):
        while True:
            while self.playlist:
                self.song = self.playlist.pop(0)
                self.player = FilePlayer(self.output, self.song['filename'])
                if info: info.set_markup(self.song.to_markup())
                times[1] = self.player.length
                self.played.append(self.song)
                for t in self.player:
                    times[0] = t
                    while self.paused:
                        time.sleep(0.01)
            self.song = self.player = None
            time.sleep(0.01)

    def get_playlist(self):
        return self.playlist

    def set_playlist(self, pl):
        self.played = []
        self.playlist = pl

    def next(self):
        if self.player: self.player.end()

    def previous(self):
        if len(self.played) >= 2:
            if self.player: self.player.end()
            self.playlist.insert(0, self.played.pop())
            self.playlist.insert(0, self.played.pop())
        elif self.player and self.played:
            if self.player: self.player.end()
            self.playlist.insert(0, self.played.pop())
        else: pass

    def go_to(self, song): pass

device = OutputDevice()
playlist = PlaylistPlayer(output = device)
