# Copyright 2004 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os, stat
import ogg.vorbis, pyid3lib
import cPickle as Pickle
from util import escape

def MusicFile(filename):
    if filename.lower().endswith(".ogg"): return OggFile(filename)
    elif filename.lower().endswith(".mp3"): return MP3File(filename)
    else: return None

class AudioFile(dict):
    def __cmp__(self, other):
        if not hasattr(other, "get"): return -1
        return (cmp(self.get("artist"), other.get("artist")) or
                cmp(self.get("album"), other.get("album")) or
                cmp(self.get("=#"), other.get("=#")) or
                cmp(self.get("title"), other.get("title")))
    
    def to_markup(self):
        title = u", ".join(self["title"].split("\n"))
        text = u'<span weight="bold" size="x-large">%s</span>' % escape(title)
        if "version" in self:
            text += u"\n         <small><b>%s</b></small>" % escape(
                self["version"])
        
        artist = u", ".join(self["artist"].split("\n"))
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
            if lfn[-4:] in ["jpeg", ".jpg", ".png", ".gif"]:
                if "front" in lfn or "cover" in lfn or "jacket" in lfn:
                   return os.path.join(base, fn)
        else: return None

class MP3File(AudioFile):

    # http://www.unixgods.org/~tilo/ID3/docs/ID3_comparison.html
    # http://www.id3.org/id3v2.4.0-frames.txt
    IDS = { "TIT1": "genre",
            "TIT2": "title",
            "TIT3": "version",
            "TPE1": "artist",
            "TPE2": "artist",
            "TPE3": "performer",
            "TPE4": "performer",
            "TCOM": "artist",
            "TEXT": "artist",
            "TLAN": "language",
            "TALB": "album",
            "TRCK": "tracknumber",
            "TSRC": "isrc",
            "TDRA": "date",
            "TDRC": "date",
            "TDOR": "date",
            "TORY": "date",
            "TCOP": "copyright",
            "TPUB": "organization",
            "WOAF": "contact",
            "WOAR": "contact",
            "WOAS": "contact",
            "WCOP": "license",
            "USER": "license",
            }
            
    def __init__(self, filename):
        if not os.path.exists(filename):
            raise ValueError("Unable to read filename: " + filename)
        self["filename"] = filename
        tag = pyid3lib.tag(filename)

        for frame in tag:
            names = self.IDS.get(frame["frameid"], [])
            if not isinstance(names, list): names = [names]
            for name in map(str.lower, names):
                try:
                    text = frame["text"]
                    for codec in ["utf-8", "shift-jis", "big5", "iso-8859-1"]:
                        try: text = text.decode(codec)
                        except (UnicodeError, LookupError): pass
                        else: break
                    else: continue
                    if name in self:
                        if text in self[name]: pass
                        elif self[name] in text: self[name] = text
                        else: self[name] += "\n" + text
                    else: self[name] = text
                    self[name] = self[name].strip()
                except: pass
        for i in ["title", "artist", "album"]:
            if hasattr(tag, i):
                self.setdefault(i, getattr(tag, i))
            if not self.get(i): self[i] = "Unknown"
        if "tracknumber" in self:
            try: self["=#"] = int(self["tracknumber"].split("/")[0])
            except: pass

class OggFile(AudioFile):
    def __init__(self, filename):
        if not os.path.exists(filename):
            raise ValueError("Unable to read filename: " + filename)
        self["filename"] = filename
        f = ogg.vorbis.VorbisFile(filename)
        for k, v in f.comment().as_dict().iteritems():
            if not isinstance(v, list): v = [v]
            v = u"\n".join(map(unicode, v))
            self[k.lower()] = v
        for i in ["title", "artist", "album"]:
            if not self.get(i): self[i] = "Unknown"
        if "tracknumber" in self:
            try: self["=#"] = int(self["tracknumber"].split("/")[0])
            except: pass
        try: del(self["vendor"])
        except KeyError: pass

class Library(dict):
    def __init__(self, initial = {}):
        dict.__init__(self, initial)

    def save(self, fn):
        f = file(fn, "w")
        songs = filter(lambda s: s and os.path.exists(s["filename"]),
                       self.values())
        Pickle.dump(songs, f, 2)
        f.close()

    def load(self, fn):
        if os.path.exists(fn): songs = Pickle.load(file(fn, "rb"))
        else: return False
        mtime = os.stat(fn)[stat.ST_MTIME] - 1
        for song in songs:
            if song and os.path.exists(song['filename']):
                self[song['filename']] = song
                if os.stat(song['filename'])[stat.ST_MTIME] > mtime:
                    self[song['filename']] = MusicFile(fn)

    def scan(self, dirs):
        for d in dirs:
            print "Checking", d
            d = os.path.expanduser(d)
            for path, dnames, fnames in os.walk(d):
                for fn in fnames:
                    m_fn = os.path.join(path, fn)
                    if m_fn in self: continue
                    m = MusicFile(m_fn)
                    if m: self[m_fn] = m

library = Library()

