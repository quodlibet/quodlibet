import os
import ogg.vorbis

def MusicFile(filename):
    if filename.lower().endswith(".mp3"): return MP3File(filename)
    elif filename.lower().endswith(".ogg"): return OggFile(filename)
    else: return None

class OggFile(dict):
    def __init__(self, filename):
        if not os.path.exists(filename):
            raise ValueError("Unable to read filename!")
        self[u"filename"] = filename
        f = ogg.vorbis.VorbisFile(filename)
        for k, v in f.comment().as_dict().iteritems():
            if not isinstance(v, list): v = [v]
            v = u"\n".join(map(unicode, v))
            self[unicode(k).lower()] = v

songs = []

def insert_file(arg, dirnames, fnames):
    for fn in fnames:
        m = MusicFile(fn)
        if m: songs.append(m)

def load(dirs):
    for d in dirs:
        d = os.path.expandvars(os.path.expanduser(d))
        os.path.walk(d, insert_file, None)
