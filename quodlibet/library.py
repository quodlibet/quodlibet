import os, stat
import ogg.vorbis, pyid3lib
import cPickle

def MusicFile(filename):
    if filename.lower().endswith(".ogg"): return OggFile(filename)
    elif filename.lower().endswith(".mp3"): return MP3File(filename)
    else: return None

def escape(str):
    return str.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

library = {}

class AudioFile(dict):
    def to_markup(self):
        title = ", ".join(self.get("title", "Unknown").split("\n"))
        text = u'<span weight="bold" size="x-large">%s</span>' % escape(title)
        if "version" in self:
            text += u"\n         <small><b>%s</b></small>" % escape(
                self["version"])
        
        artist = ", ".join(self.get("artist", "Unknown").split("\n"))
        text += u"\n      <small>by %s</small>" % escape(artist)
        if "album" in self:
            album = u"\n   <b>%s</b>" % escape(self["album"])
            if "tracknumber" in self:
                album += u" - Track %s" % escape(self["tracknumber"])
            text += album
        return text

    def find_cover(self):
        base = os.path.split(self['filename'])[0]
        fns = os.listdir(base)
        fns.sort()
        for fn in fns:
            lfn = fn.lower()
            if lfn[-4:] in ["jpeg", ".jpg", ".png", "gif"]:
                if "front" in fn or "cover" in fn:
                   return os.path.join(base, fn)
        else: return None

class MP3File(AudioFile):

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
                    text = frame["text"]
                    for codec in ["utf-8", "shift-jis", "big5", "iso-8859-1"]:
                        try: text = text.decode(codec)
                        except (UnicodeError, LookupError): pass
                        else: break
                    else: continue
                    if name in self: self[name] += "\n" + text
                    else: self[name] = text
                    self[name] = self[name].strip()
                except: pass
        for i in ["title", "artist", "album"]:
            if hasattr(tag, i):
                self.setdefault(i, getattr(tag, i))

class OggFile(AudioFile):
    def __init__(self, filename):
        if not os.path.exists(filename):
            raise ValueError("Unable to read filename: " + filename)
        self[u"filename"] = filename
        f = ogg.vorbis.VorbisFile(filename)
        for k, v in f.comment().as_dict().iteritems():
            if not isinstance(v, list): v = [v]
            v = u"\n".join(map(unicode, v))
            self[k.lower()] = v

def load_cache():
    fn = os.path.join(os.environ["HOME"], ".quodlibet", "songs")
    if os.path.exists(fn): songs = cPickle.load(file(fn, "rb"))
    else: return []
    mtime = os.stat(fn)[stat.ST_MTIME] - 1
    nsongs = []
    for song in songs:
        if song and os.path.exists(song['filename']):
            library[song['filename']] = song
            if os.stat(song['filename'])[stat.ST_MTIME] > mtime:
                library[song['filename']] = MusicFile(fn)
            nsongs.append(library[song['filename']])
    return nsongs

def save_cache(songs):
    songs = filter(None, songs)
    fn = os.path.join(os.environ["HOME"], ".quodlibet", "songs")
    if not os.path.isdir(os.path.split(fn)[0]):
        os.mkdir(os.path.split(fn)[0])
    f = file(fn, "w")
    cPickle.dump(songs, f, 2)
    f.close()

def load(dirs):
    for d in dirs:
        print "Checking", d
        d = os.path.expanduser(d)
        for path, dnames, fnames in os.walk(d):
            for fn in fnames:
                m_fn = os.path.join(path, fn)
                if m_fn in library: continue
                m = MusicFile(m_fn)
                if m:
                    library[m_fn] = m
