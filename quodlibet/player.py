import mad
import ao
import ogg.vorbis
import time
import ossaudiodev # barf
queue = []
playlist = []
orig_playlist = []
paused = False
shuffled = False
repeat = False

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
        self.length = self.mf.total_time()

    def __iter__(self): return self

    def seek(self, ms):
        self.audio.seek_time(ms)

    def next(self):
        if self.stopped: raise StopIteration
        buff = self.audio.read(4096)
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
        (buff, bytes, bit) = self.audio.read(4096)
        if bytes == 0: raise StopIteration
        self.dev.play(buff, bytes)
        return self.audio.time_tell() * 1000

def Player(dev, filename):
    kind = filename.split(".")[-1].lower()
    return { "ogg": OggPlayer,
             "mp3": MP3Player }[kind](dev, filename)

def get_volume():
    return ossaudiodev.openmixer().get(ossaudiodev.SOUND_MIXER_PCM)[0]

def get_device(samplerate = None):
    return ao.AudioDevice(ao.driver_id('oss'))

def set_volume(song, value):
    ossaudiodev.openmixer().set(ossaudiodev.SOUND_MIXER_PCM, (value, value))

def set_playlist(songs):
    del(playlist[:])
    del(orig_playlist[:])
    playlist.extend(songs)
    orig_playlist.extend(songs)

def go_to_song(song, newsong):
    if song in playlist: playlist.remove(newsong)
    playlist.insert(0, newsong)
    song.end()

def play(info):
    dev = get_device()
    while True:
        do_queue(None)
        while playlist:
            if shuffled: random.shuffle(playlist)
            song = playlist.pop(0)
            player = Player(dev, song['filename'])
            info.set_markup(song.to_markup())
            times[1] = player.length
            for t in player:
                times[0] = t
                do_queue(player)
                while paused:
                    do_queue(player)
                    time.sleep(0.01)
                else: continue
                break

            if song in playlist: playlist.remove(song)
        if repeat: playlist.extend(orig_playlist)

        time.sleep(0.01)

COMMANDS = { "seek": (lambda *args: args[0] and AudioPlayer.seek(*args)),
             "goto": go_to_song,
             "next": (lambda *args: args[0] and AudioPlayer.end(*args)),
             "volume": set_volume }

def do_queue(song):
    while queue:
        command = queue.pop(0)
        COMMANDS[command[0]](*((song,) + command[1]))
