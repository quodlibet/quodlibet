import os
import ogg.vorbis, pyid3lib

def MusicFile(filename):
    if filename.lower().endswith(".ogg"): return OggFile(filename)
    elif filename.lower().endswith(".mp3"): return MP3File(filename)
    else: return None

class MP3File(dict):

    # http://www.unixgods.org/~tilo/ID3/docs/ID3_comparison.html
    # http://www.id3.org/id3v2.4.0-frames.txt
    IDS = { "TIT1": "genre",
            "TIT2": "title",
            "TIT3": "version",
            "TPE1": "artist",
            "TPE4": ("artist", "performer"),
            "TCOM": "artist",
            "TEXT": "artist",
            "TPE2": ("artist", "performer"),
            "TPE3": "performer",
            "TLAN": "language",
            "TALB": "album",
            "TRCK": "tracknumber",
            "TSRC": "ISRC",
            "TDRA": "date",
            "TDRC": "date",
            "TDOR": "date",
            "TORY": "date",
            "TCOP": ("copyright", "license"),
            "TPUB": "organization",
            "WOAF": "contact",
            "WOAR": "contact",
            "WOAS": "contact",
            "WCOP": ("copyright", "license"),
            "USER": ("copyright", "license"),
            }
            
    def __init__(self, filename):
        if not os.path.exists(filename):
            raise ValueError("Unable to read filename: " + filename)
        self[u"filename"] = filename
        tag = pyid3lib.tag(filename)

        for frame in tag:
            name = self.IDS.get(frame["frameid"])
            if name:
                try:
                    name = unicode(name.lower())
                    text = frame["text"].decode("iso-8859-1")
                    if name in self: self[name] += "\n" + text
                    else: self[name] = text
                except: pass
        for i in ["title", "artist", "album"]:
            if hasattr(tag, i):
                self.setdefault(unicode(i), getattr(tag, i))

class OggFile(dict):
    def __init__(self, filename):
        if not os.path.exists(filename):
            raise ValueError("Unable to read filename: " + filename)
        self[u"filename"] = filename
        f = ogg.vorbis.VorbisFile(filename)
        for k, v in f.comment().as_dict().iteritems():
            if not isinstance(v, list): v = [v]
            v = u"\n".join(map(unicode, v))
            self[unicode(k).lower()] = v

songs = []

def load(dirs):
    for d in dirs:
        print "Checking", d
        d = os.path.expanduser(d)
        for path, dnames, fnames in os.walk(d):
            for fn in fnames:
                m = MusicFile(os.path.join(path, fn))
                if m: songs.append(m)
