# Copyright 2004 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os, stat
import cPickle as Pickle
import util; from util import escape
import time

def MusicFile(filename):
    typ = filename[-4:].lower()
    if typ in supported: return supported[typ](filename)
    else: return None

class AudioFile(dict):
    def __cmp__(self, other):
        if not hasattr(other, "get"):
            raise ValueError("songs can only be compared to other songs.")
        return (cmp(self.get("album"), other.get("album")) or
                cmp(self.get("=#"), other.get("=#")) or
                cmp(self.get("artist"), other.get("artist")) or
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

    def get_played(self):
        count = self["=playcount"]    
        if count == 0: return "Never"
        else:
            t = time.localtime(self["=lastplayed"])
            tstr = time.strftime("%F, %X", t)
            return "%d times, recently on %s" % (count, tstr)

    def to_dump(self):
        s = ""
        for k, v in self.items():
            if k[0] == "=": continue
            for v2 in v.split("\n"):
                s += "%s=%s\n" % (k, v2)
        return s

    def change(key, old_value, new_value):
        parts = self[key].split("\n")
        parts[parts.index(old_value)] = new_value
        self[key] = "\n".join(parts)
        if key == "tracknumber":
            try: self["=#"] = int(self["tracknumber"].split("/")[0])
            except ValueError:
                try: del(self["=#"])
                except KeyError: pass

    def add(key, value):
        if key in self: self[key] = value
        else: self[key] += "\n" + value
        if key == "tracknumber":
            try: self["=#"] = int(self["tracknumber"].split("/")[0])
            except ValueError:
                try: del(self["=#"])
                except KeyError: pass

    def remove(key, value):
        if self[key] == value: del(self[key])
        else:
            parts = self[key].split("\n")
            parts.remove(value)
            self[key] = "\n".join(parts)
        if key == "tracknumber":
            try: self["=#"] = int(self["tracknumber"].split("/")[0])
            except ValueError:
                try: del(self["=#"])
                except KeyError: pass

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
            "TPE2": "performer",
            "TPE3": "performer",
            "TPE4": "performer",
            "TLAN": "language",
            "TALB": "album",
            "TRCK": "tracknumber",
            "TPOS": "discnumber",
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

    INVERT_IDS = { "genre": "TIT1",
                   "title": "TIT2",
                   "version": "TIT3",
                   "language": "TLAN",
                   "isrc": "TSRC",
                   "tracknumber": "TRCK",
                   "artist": "TPE1",
                   "discnumber": "TPOS",
                   "organization": "TPUB",
                   "album": "TALB"
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
        self.setdefault("=lastplayed", 0)
        self.setdefault("=playcount", 0)

    def write(self):
        tag = pyid3lib.tag(self['filename'])
        for key, id3name in self.INVERT_IDS.items():
            try:
                while True: tag.remove(id3name)
            except ValueError: pass
            if key in self:
                for value in self[key].split("\n"):
                    try: value = value.encode("iso-8859-1")
                    except UnicodeError: value = value.encode("utf-8")
                    tag.append({'frameid': id3name, 'text': value })
        tag.update()
        self["=mtime"] = int(os.stat(self['filename'])[stat.ST_MTIME])


    def can_change(self, k):
        return k in self.INVERT_IDS.keys()

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
        self.setdefault("=lastplayed", 0)
        self.setdefault("=playcount", 0)

    def write(self):
        f = ogg.vorbis.VorbisFile(self['filename'])
        comments = f.comment()
        comments.clear()
        for key in self.keys():
            if key == "filename" or key[0] == "=": continue
            else:
                value = self[key]
                if not isinstance(value, list): value = value.split("\n")
                if len(value) == 1: value = value[0]
                comments[key] = value
        comments.write_to(self['filename'])
        self["=mtime"] = int(os.stat(self['filename'])[stat.ST_MTIME])

    def can_change(self, k):
        return k not in ["vendor", "filename"]

class AudioFileGroup(dict):

    class Comment(unicode):
        complete = True
        def __repr__(self):
            return '%s %s' % (str(self), self.paren())

        def __str__(self):
            return self.replace('&','&amp;')\
                    .replace('<','&lt;').replace('>','&gt;')

        def paren(self):
            if self.shared and self.complete:
                return '(shared across all %d songs)' % self.total
            elif self.shared:
                return '(missing from %d songs)' % self.missing
            elif self.complete:
                return '(different across %d songs)' % self.total
            else:
                return '(different across %d songs, missing from %d songs)' % (
                        self.have, self.missing)

        def safenicestr(self):
            if self.shared and self.complete: return str(self)
            elif self.shared: return '%s <i>%s</i>' % (str(self), self.paren())
            else: return '<i>%s</i>' % self.paren()

    class SharedComment(Comment): shared = True
    class UnsharedComment(Comment): shared = False
    class PartialSharedComment(SharedComment): complete = False
    class PartialUnsharedComment(UnsharedComment): complete = False

    def __init__(self, songs):
        self.songcount = total = len(songs)
        keys = {}
        first = {}
        all = {}
        self.types = {}

        # collect types of songs; comment names, values, and sharedness
        for song in songs:
            self.types[repr(song.__class__)] = song # for group can_change
            for comment, value in song.iteritems():
                keys[comment] = keys.get(comment, 0) + 1
                first.setdefault(comment, value)
                all[comment] = all.get(comment, True) and first[comment] == value

        # collect comment representations
        for comment, count in keys.iteritems():
            if count < total:
                if all[comment]:
                    value = self.PartialSharedComment(first[comment])
                else:
                    value = self.PartialUnsharedComment(first[comment])
            else:
                if all[comment]:
                    value = self.SharedComment(first[comment])
                else:
                    value = self.UnsharedComment(first[comment])
            value.have = count
            value.total = total
            value.missing = total - count

            self[comment] = value

    def can_change(self, k=None):
        if k is None:
            can = True
            for song in self.types.itervalues():
                cantoo = song.can_change()
                if can is True: can = cantoo
                elif cantoo is True: pass
                else: can = dict.from_keys(can+cantoo).keys()
        else:
            can = min([song.can_change(k) for song in self.types.itervalues()])
        return can


class Library(dict):
    def __init__(self, initial = {}):
        dict.__init__(self, initial)

    def remove(self, song):
        del(self[song['filename']])

    def save(self, fn):
        util.mkdir(os.path.dirname(fn))
        f = file(fn, "w")
        songs = filter(lambda s: s and os.path.exists(s["filename"]),
                       self.values())
        Pickle.dump(songs, f, 2)
        f.close()

    def load(self, fn):
        if os.path.exists(fn): songs = Pickle.load(file(fn, "rb"))
        else: return 0, 0
        removed, changed = 0, 0
        for song in songs:
            fn = song['filename']
            if song and os.path.exists(fn):
                if (os.stat(fn)[stat.ST_MTIME] != song["=mtime"]):
                    self[fn] = MusicFile(fn)
                    self[fn]["=mtime"] = int(os.stat(fn)[stat.ST_MTIME])
                    changed += 1
                else:
                    song.setdefault("=lastplayed", 0)
                    song.setdefault("=playcount", 0)
                    self[fn] = song
            else:
                removed += 1
        return changed, removed

    def scan(self, dirs):
        added, changed = 0, 0
        for d in dirs:
            print "Checking", d
            d = os.path.expanduser(d)
            for path, dnames, fnames in os.walk(d):
                for fn in fnames:
                    m_fn = os.path.join(path, fn)
                    if m_fn in self:
                        m = self[m_fn]
                        if os.stat(m_fn)[stat.ST_MTIME] == m["=mtime"]:
                            continue
                        else:
                            changed += 1
                            added -= 1
                    m = MusicFile(m_fn)
                    if m:
                        added += 1
                        m["=mtime"] = int(os.stat(m_fn)[stat.ST_MTIME])
                        self[m_fn] = m
                yield added, changed

supported = {}

if util.check_ogg():
    print "Enabling Ogg Vorbis support."
    import ogg.vorbis
    supported[".ogg"] = OggFile
else:
    print "W: Ogg Vorbis support is disabled! Ogg files cannot be loaded."

if util.check_mp3():
    print "Enabling MP3 support."
    import pyid3lib
    supported[".mp3"] = MP3File
else:
    print "W: MP3 support is disabled! MP3 files cannot be loaded."

library = Library()

