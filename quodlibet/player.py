import mad
import ao
import ogg.vorbis
import time

queue = []
playlist = []
paused = False
shuffled = False

times = [0, 0]

class MP3Player(object):
    def __init__(self, dev, filename):
        self.dev = dev
        self.mf = mad.MadFile(filename)
        self.length = self.mf.total_time()

    def __iter__(self): return self

    def seek(self, ms):
        self.mf.seek_time(ms)

    def next(self):
        buff = self.mf.read()
        if buff is None: raise StopIteration
        self.dev.play(buff, len(buff))
        return self.mf.current_time()

class OggPlayer(object):
    def __init__(self, dev, filename):
        self.dev = dev
        self.vf = ogg.vorbis.VorbisFile(filename)
        self.length = self.vf.time_total(-1) * 1000

    def __iter__(self): return self

    def seek(self, ms):
        self.vf.time_seek(ms / 1000.0)

    def next(self):
        (buff, bytes, bit) = self.vf.read(1048576)
        if bytes == 0: raise StopIteration
        self.dev.play(buff, bytes)
        return self.vf.time_tell() * 1000

def Player(dev, filename):
    kind = filename.split(".")[-1].lower()
    return { "ogg": OggPlayer,
             "mp3": MP3Player }[kind](dev, filename)

def get_device(samplerate = None):
    return ao.AudioDevice(ao.driver_id('oss'))

def set_playlist(songs):
    del(playlist[:])
    playlist.extend(songs)

def play():
    dev = get_device()
    while True:
        do_queue(None)
        while playlist:
            song = playlist.pop(0)
            player = Player(dev, song['filename'])
            times[1] = player.length
            for t in player:
                times[0] = t
                do_queue(player)
                while paused:
                    do_queue(player)
                    time.sleep(0.01)

        time.sleep(0.01)

def seek(song, pos):
    if song: song.seek(pos)

COMMANDS = { "seek": seek }

def do_queue(song):
    while queue:
        command = queue.pop(0)
        COMMANDS[command[0]](*((song,) + command[1]))
