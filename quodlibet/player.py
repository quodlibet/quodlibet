import mad
import ao
import ogg.vorbis
import time

queue = []
playlist = []
paused = False
shuffled = False

class MP3Player(object):
    def __init__(self, dev, filename):
        self.dev = dev
        self.mf = mad.MadFile(filename)
        self.length = self.mf.total_time()

    def __iter__(self): return self

    def next(self):
        buff = self.mf.read()
        if buff is None: raise StopIteration
        self.dev.play(buff, len(buff))
        return self.mf.current_time()
        

class OggPlayer(object):
    def __init__(self, dev, filename):
        self.dev = dev
        self.vf = ogg.vorbis.VorbisFile(filename)
        self.length = 1000

    def __iter__(self): return self

    def next(self):
        (buff, bytes, bit) = self.vf.read(1048576)
        if bytes == 0: raise StopIteration
        self.dev.play(buff, bytes)
        return 1000

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
        do_queue()
        while playlist:
            song = playlist.pop(0)['filename']
            player = Player(dev, song)
            for t in player:
                do_queue()
                while paused:
                    do_queue()
                    time.sleep(0.01)

        time.sleep(0.01)

def do_queue():
    for command in queue:
        COMMANDS[queue[0]](*queue[1:])
