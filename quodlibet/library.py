# Copyright 2004 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os, sys
import cPickle as Pickle
import util; from util import escape
import fcntl
import random
import time
import shutil
import gettext
import config
import tempfile
import parser
import sre
_ = gettext.gettext

if sys.version_info < (2, 4):
    from sets import Set as set

class Unknown(unicode): pass
UNKNOWN = Unknown(_("Unknown"))

def MusicFile(filename):
    for ext in supported.keys():
        if filename.lower().endswith(ext):
            try:
                return supported[ext](filename)
            except:
                print _("W: Error loading %s") % filename
                return None
    else: return None

global library
library = None

class AudioFile(dict):
    def __cmp__(self, other):
        if not other: return -1
        return (cmp(self("album"), other("album")) or
                cmp(self("~#disc"), other("~#disc")) or
                cmp(self("~#track"), other("~#track")) or
                cmp(self("artist"), other("artist")) or
                cmp(self("title"), other("title")) or
                cmp(self("~filename"), other("~filename")))

    # True if our key's value is actually unknown, rather than just the
    # string "Unknown". Or true if we don't know the key at all.
    def unknown(self, key):
        return isinstance(self.get(key, Unknown()), Unknown)

    def realkeys(self):
        return filter(lambda s: s and s[0] != "~" and not self.unknown(s),
                      self.keys())

    def __call__(self, key, default = ""):
        if key and key[0] == "~":
            key = key[1:]
            if "~" in key:
                parts = [self(p) for p in key.split("~")]
                return " - ".join(filter(None, parts))
            elif key == "basename": return os.path.basename(self["~filename"])
            elif key == "dirname": return os.path.dirname(self["~filename"])
            elif key == "length": return util.format_time(self["~#length"])
            elif key == "#track":
                try: return int(self["tracknumber"].split("/")[0])
                except (ValueError, TypeError, KeyError): return default
            elif key == "#disc":
                try: return int(self["discnumber"].split("/")[0])
                except (ValueError, TypeError, KeyError): return default
            elif key[0] == "#" and "~" + key not in self:
                try: return int(self[key[1:]])
                except (ValueError, TypeError, KeyError): return default
            else: return dict.get(self, "~" + key, default)
        elif key == "title":
            v = dict.get(self, "title")
            if v is None:
                return "%s [%s]" %(
                    os.path.basename(self["~filename"]), UNKNOWN)
            else: return v
        elif (key == "artist" or key == "album"):
            v = dict.get(self, key)
            if v is None: return UNKNOWN
            else: return v
        else: return dict.get(self, key, default)

    def comma(self, key):
        v = self(key, "")
        if isinstance(v, int): return v
        else: return v.replace("\n", ", ")

    def list(self, key):
        if key in self: return self[key].split("\n")
        else: return []

    # copy important keys from the other song to this one.
    def migrate(self, other):
        for key in ["~#playcount", "~#lastplayed"]:
            self[key] = other[key]
        for key in filter(lambda s: s.startswith("~#playlist_"), other):
            self[key] = other[key]

    def exists(self):
        return os.path.exists(self["~filename"])

    def valid(self):
        return (self.exists() and
                self["~#mtime"] == os.path.mtime(self["~filename"]))

    def can_change(self, k = None):
        if k is None: return True
        else: return (k and k != "vendor" and "=" not in k and "~" not in k)

    def rename(self, newname):
        if newname[0] == os.sep: util.mkdir(os.path.dirname(newname))
        else: newname = os.path.join(self('~dirname'), newname)
        if not os.path.exists(newname):
            shutil.move(self['~filename'], newname)
        elif newname != self['~filename']: raise ValueError
        self.sanitize(newname)

    def website(self):
        if "website" in self: return self.list("website")[0]
        for cont in self.list("contact") + self.list("comment"):
            c = cont.lower()
            if (c.startswith("http://") or c.startswith("https://") or
                c.startswith("www.")): return cont
            elif c.startswith("//www."): return "http:" + cont
        else:
            text = "http://www.google.com/search?q="
            esc = lambda c: ord(c) > 127 and '%%%x'%ord(c) or c
            if "labelid" in self: text += esc(self["labelid"])
            else:
                artist = util.escape("+".join(self("artist").split()))
                album = util.escape("+".join(self("album").split()))
                artist = util.encode(artist)
                album = util.encode(album)
                artist = "%22" + ''.join(map(esc, artist)) + "%22"
                album = "%22" + ''.join(map(esc, album)) + "%22"
                text += artist + "+" + album
            text += "&ie=UTF8"
            return text

    # Sanity-check all sorts of things...
    def sanitize(self, filename = None):
        if filename: self["~filename"] = filename
        elif "~filename" not in self: raise ValueError("Unknown filename!")

        # Fill in necessary values.
        self.setdefault("~#lastplayed", 0)
        self.setdefault("~#playcount", 0)
        self.setdefault("~#length", 0)

        # Clean up Vorbis garbage.
        try: del(self["vendor"])
        except KeyError: pass

        self["~#mtime"] = os.path.mtime(self['~filename'])

    # Construct the text seen in the player window
    def to_markup(self):
        title = self.comma("title")
        text = u'<span weight="bold" size="large">%s</span>' % escape(title)
        if "version" in self:
            text += u"\n<small><b>%s</b></small>" % escape(
                self.comma("version"))

        if not self.unknown("artist"):
            text += u"\n" + _("by %s") % escape(self.comma("artist"))

        if "performer" in self:
            s = _("Performed by %s") % self.comma("performer")
            text += "\n<small>%s</small>" % s

        others = ""
        if "arranger" in self:
            others += "; " + _("arranged by %s") % self.comma("arranger")
        if "lyricist" in self:
            others += "; " + _("lyrics by %s") % self.comma("lyricist")
        if "conductor" in self:
            others += "; " + _("conducted by %s") % self.comma("conductor")
        if "composer" in self:
            others += "; " + _("composed by %s") % self.comma("composer")
        if "author" in self:
            others += "; " + _("written by %s") % self.comma("author")

        if others:
            others = others.lstrip("; ")
            others = others[0].upper() + others[1:]
            text += "\n<small>%s</small>" % escape(others)

        if not self.unknown("album"):
            album = u"\n<b>%s</b>" % escape(self.comma("album"))
            if "discnumber" in self:
                album += " - "+_("Disc %s")%escape(self.comma("discnumber"))
            if "part" in self:
                album += u" - <b>%s</b>" % escape(self.comma("part"))
            if "tracknumber" in self:
                album +=" - " + _("Track %s")%escape(self.comma("tracknumber"))
            text += album
        return text

    # A shortened song info line (for the statusicon tooltip)
    def to_short(self):
        if self.unknown("album"):
            return self.comma("~artist~title~version")
        else:
            return self.comma("~album~discnumber~part"
                              "~tracknumber~title~version")

    # Nicely format how long it's been since it was played
    def get_played(self):
        count = self["~#playcount"]    
        if count == 0: return _("Never")
        else:
            t = time.localtime(self["~#lastplayed"])
            tstr = time.strftime("%F, %X", t)
            if count == 1:
                return _("1 time, recently on %s") % tstr
            else:
                return _("%d times, recently on %s") % (count, tstr)

    # key=value list, for ~/.quodlibet/current interface
    def to_dump(self):
        s = ""
        for k in self.realkeys():
            for v2 in self.list(k):
                s += "%s=%s\n" % (k, util.encode(v2))
        return s

    # Try to change a value in the data to a new value; if the
    # value being changed from doesn't exist, just overwrite the
    # whole value.
    def change(self, key, old_value, new_value):
        try:
            parts = self.list(key)
            try: parts[parts.index(old_value)] = new_value
            except ValueError:
                self[key] = new_value
            else:
                self[key] = "\n".join(parts)
        except KeyError: self[key] = new_value
        self.sanitize()

    def add(self, key, value):
        if self.unknown(key): self[key] = value
        else: self[key] += "\n" + value
        self.sanitize()

    # Like change, if the value isn't found, remove all values...
    def remove(self, key, value):
        if self[key] == value: del(self[key])
        else:
            try:
                parts = self.list(key)
                parts.remove(value)
                self[key] = "\n".join(parts)
            except ValueError:
                if key in self: del(self[key])
        self.sanitize()

    # Try to find an album cover for the file
    def find_cover(self):
        base = self('~dirname')
        fns = os.listdir(base)
        images = []
        fns.sort()
        for fn in fns:
            lfn = fn.lower()
            if lfn[-4:] in ["jpeg", ".jpg", ".png", ".gif"]:
                # Look for some generic names, and also the album
                # label number, which is pretty common. Label number
                # is worth 2 points, everything else 1.
                matches = filter(lambda s: s in lfn,
                                 ["front", "cover", "jacket", "folder",
                                  self.get("labelid", lfn + ".").lower(),
                                  self.get("labelid", lfn + ".").lower()])
                score = len(matches)
                if score: images.append((score, os.path.join(base, fn)))
        # Highest score wins.
        if images: return max(images)[1]
        elif "~picture" in self:
            # Otherwise, we might have a picture stored in the metadata...
            import pyid3lib
            f = tempfile.NamedTemporaryFile()
            tag = pyid3lib.tag(self['~filename'])
            for frame in tag:
                if frame["frameid"] == "APIC":
                    f.write(frame["data"])
                    f.flush()
                    return f
            else:
                f.close()
                return None
        else: return None

class MPCFile(AudioFile):
    # Map APE names to QL names. APE tags are also usually capitalized.

    IGNORE = ["file", "index", "introplay", "dummy"]
    TRANS = { "subtitle": "version",
              "track": "tracknumber",
              "catalog": "labelid",
              "year": "date",
              "record location": "location"
              }
    SNART = dict([(v, k) for k, v in TRANS.iteritems()])
    
    def __init__(self, filename):
        import musepack
        tag = musepack.APETag(filename)
        for key, value in tag:
            key = MPCFile.TRANS.get(key.lower(), key.lower())
            if value.kind == musepack.apev2.TEXT and key not in MPCFile.IGNORE:
                self[key] = "\n".join(list(value))
        f = musepack.MPCFile(filename)
        self["~#length"] = int(f.length / 1000)
        self.sanitize(filename)

    def can_change(self, key = None):
        if key is None: return True
        else: return (AudioFile.can_change(self, key) and
                      key not in MPCFile.IGNORE)

    def write(self):
        import musepack
        tag = musepack.APETag(self['~filename'])

        keys = tag.keys()
        for key in keys:
            # remove any text keys we read in
            value = tag[key]
            if value.kind == musepack.apev2.TEXT and key not in MPCFile.IGNORE:
                del(tag[key])
        for key in self.realkeys():
            value = self[key]
            key = MPCFile.SNART.get(key, key)
            if key in ["isrc", "isbn", "ean/upc"]: key = key.upper()
            else: key = key.title()
            tag[key] = value.split("\n")
        tag.write()

class MP3File(AudioFile):

    # http://www.unixgods.org/~tilo/ID3/docs/ID3_comparison.html
    # http://www.id3.org/id3v2.4.0-frames.txt
    IDS = { "TIT1": "genre",
            "TIT2": "title",
            "TIT3": "version",
            "TPE1": "artist",
            "TPE2": "performer", 
            "TPE3": "conductor",
            "TPE4": "arranger",
            "TEXT": "lyricist",
            "TCOM": "composer",
            "TENC": "encodedby",
            "TLAN": "language",
            "TALB": "album",
            "TRCK": "tracknumber",
            "TPOS": "discnumber",
            "TSRC": "isrc",
            "TCOP": "copyright",
            "TPUB": "organization",
            "USER": "license",
            "WOAR": "website",
            "TOLY": "author",
            "COMM": "comment",
            }

    INVERT_IDS = dict([(v, k) for k, v in IDS.iteritems()])
            
    def __init__(self, filename):
        import pyid3lib, mad
        if not os.path.exists(filename):
            raise ValueError("Unable to read filename: " + filename)
        tag = pyid3lib.tag(filename)
        date = ["", "", ""]

        for frame in tag:
            if frame["frameid"] == "TDAT" and len(frame["text"]) == 4:
                date[1] = frame["text"][0:2]
                date[2] = frame["text"][2:4]
                continue
            elif frame["frameid"] == "TYER" and len(frame["text"]) == 4:
                date[0] = frame["text"]
                continue
            elif frame["frameid"] == "APIC" and frame["data"]:
                self["~picture"] = "y"
                continue
            elif frame["frameid"] == "COMM":
                if frame["description"].startswith("QuodLibet::"):
                    name = frame["description"][11:]
                elif frame["description"] == "ID3v1 Comment": continue
                else: name = "comment"
            else: name = self.IDS.get(frame["frameid"], "").lower()

            if not name: continue

            try:
                text = frame["text"]
                if not text: continue
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

        md = mad.MadFile(filename)
        self["~#length"] = md.total_time() // 1000
        if date[0]: self["date"] = "-".join(filter(None, date))
        self.sanitize(filename)

    def write(self):
        import pyid3lib
        tag = pyid3lib.tag(self['~filename'])

        ql_comments = [i for i, frame in enumerate(tag)
                       if (frame["frameid"] == "COMM" and
                           frame["description"].startswith("QuodLibet::"))]
        ql_comments.reverse()
        for comm in ql_comments: del(tag[comm])
        
        for key, id3name in self.INVERT_IDS.items():
            try:
                while True: tag.remove(id3name)
            except ValueError: pass
            if key in self:
                if self.unknown(key): continue
                for value in self.list(key):
                    value = value.encode("utf-8")
                    tag.append({'frameid': id3name, 'text': value })

        for key in filter(lambda x: x not in self.INVERT_IDS and x != "date",
                          self.realkeys()):
            for value in self.list(key):
                value = value.encode('utf-8')
                tag.append({'frameid': "COMM", 'text': value,
                            'description': "QuodLibet::%s" % key})

        for date in self.list("date"):
            y, m, d = (date + "--").split("-")[0:3]
            if y:
                try:
                    while True: tag.remove("TYER")
                except ValueError: pass
                tag.append({'frameid': "TYER", 'text': str(y)})
            if m and d:
                try:
                    while True: tag.remove("TDAT")
                except ValueError: pass
                tag.append({'frameid': "TDAT", 'text': str(m+d)})
                
        tag.update()
        self["~#mtime"] = os.path.mtime(self['~filename'])

class OggFile(AudioFile):
    def __init__(self, filename):
        import ogg.vorbis
        if not os.path.exists(filename):
            raise ValueError("Unable to read filename: " + filename)
        f = ogg.vorbis.VorbisFile(filename)
        for k, v in f.comment().as_dict().iteritems():
            if not isinstance(v, list): v = [v]
            v = u"\n".join(map(unicode, v))
            self[k.lower()] = v
        self["~#length"] = int(f.time_total(-1))
        self.sanitize(filename)

    def write(self):
        import ogg.vorbis
        f = ogg.vorbis.VorbisFile(self['~filename'])
        comments = f.comment()
        comments.clear()
        for key in self.realkeys():
            value = self.list(key)
            for line in value: comments[key] = line
        comments.write_to(self['~filename'])
        self["~#mtime"] = os.path.mtime(self['~filename'])

class ModFile(AudioFile):
    def __init__(self, filename):
        import modplug
        f = modplug.ModFile(filename)
        self["~#length"] = f.length // 1000
        try: self["title"] = f.title.decode("utf-8")
        except UnicodeError: self["title"] = f.title.decode("iso-8859-1")
        self.sanitize(filename)

    def write(self):
        raise TypeError("ModFiles do not support writing!")

    def can_change(self, k = None):
        if k is None: return []
        else: return False

class FLACFile(AudioFile):
    def __init__(self, filename):
        import flac.metadata
        if not os.path.exists(filename):
            raise ValueError("Unable to read filename: " + filename)
        chain = flac.metadata.Chain()
        chain.read(filename)
        it = flac.metadata.Iterator()
        it.init(chain)
        vc = None
        while True:
            if it.get_block_type() == flac.metadata.VORBIS_COMMENT:
                block = it.get_block()
                vc = flac.metadata.VorbisComment(block)
            elif it.get_block_type() == flac.metadata.STREAMINFO:
                info = it.get_block().data.stream_info
                self["~#length"] = (info.total_samples // info.sample_rate)
            if not it.next(): break

        if vc:
            for k in vc.comments:
                parts = k.split("=")
                key = parts[0].lower()
                val = util.decode("=".join(parts[1:]))
                if key in self: self[key] += "\n" + val
                else: self[key] = val
        self.sanitize(filename)

    def write(self):
        import flac.metadata
        chain = flac.metadata.Chain()
        chain.read(self['~filename'])
        it = flac.metadata.Iterator()
        it.init(chain)
        vc = None
        while True:
            if it.get_block_type() == flac.metadata.VORBIS_COMMENT:
                block = it.get_block()
                vc = flac.metadata.VorbisComment(block)
                break
            if not it.next(): break

        if vc:
            keys = [k.split("=")[0] for k in vc.comments]
            for k in keys: del(vc.comments[k])
            for key in self.realkeys():
                value = self.list(key)
                for line in value:
                    vc.comments[key] = util.encode(line)
            chain.write(True, True)

class AudioFileGroup(dict):

    class Comment(unicode):
        complete = True
        def __repr__(self):
            return '%s %s' % (str(self), self.paren())

        def __str__(self):
            return util.escape(self)

        def paren(self):
            if self.shared and self.complete:
                return _('(shared across all %d songs)') % self.total
            elif self.shared:
                return _('(missing from %d songs)') % self.missing
            elif self.complete:
                return _('(different across %d songs)') % self.total
            else:
                return _('(different across %d songs, missing from %d songs)')%(
                        self.have, self.missing)

        def safenicestr(self):
            if self.shared and self.complete: return str(self)
            elif self.shared: return '%s <i>%s</i>' % (str(self), self.paren())
            else: return '<i>%s</i>' % self.paren()

    class SharedComment(Comment): shared = True
    class UnsharedComment(Comment): shared = False
    class PartialSharedComment(SharedComment): complete = False
    class PartialUnsharedComment(UnsharedComment): complete = False

    def realkeys(self):
        return filter(lambda s: s and "~" not in s and "=" not in s, self)

    def __init__(self, songs):
        self.songcount = total = len(songs)
        keys = {}
        first = {}
        all = {}
        self.types = {}

        # collect types of songs; comment names, values, and sharedness
        for song in songs:
            self.types[song.__class__] = song # for group can_change
            for comment, val in song.iteritems():
                keys[comment] = keys.get(comment, 0) + 1
                first.setdefault(comment, val)
                all[comment] = all.get(comment, True) and first[comment] == val

        # collect comment representations
        for comment, count in keys.iteritems():
            if count < total:
                if all[comment]:
                    value = self.PartialSharedComment(first[comment])
                else:
                    value = self.PartialUnsharedComment(first[comment])
            else:
                decoded = first[comment]
                if isinstance(decoded, str): decoded = util.decode(decoded)
                if all[comment]: value = self.SharedComment(decoded)
                else: value = self.UnsharedComment(decoded)
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
                else: can = set(can+cantoo)
        else:
            can = min([song.can_change(k) for song in self.types.itervalues()])
        return can

class Library(dict):
    def __init__(self, masked = [], initial = {}):
        self.masked = masked
        self.masked_files = {}
        dict.__init__(self, initial)

    def random(self, tag):
        songs = {}
        for song in self.values():
             if not song.unknown(tag):
                 for v in song.list(tag): songs[v] = True  
        return random.choice(songs.keys())

    def rename(self, song, newfn):
        oldfn = song['~filename']
        song.rename(newfn)
        del(self[oldfn])
        self[song['~filename']] = song

    def remove(self, song):
        del(self[song['~filename']])

    def add(self, fn):
        if fn not in self:
            song = MusicFile(fn)
            if song: self[fn] = song
            return bool(song)
        else: return True

    def query(self, text, sort = None):
        if text == "": songs = self.values()
        elif "#" not in text and "=" not in text and "/" not in text:
            # Simple, non-regexp search
            parts = ["* = /" + sre.escape(p) + "/" for p in text.split()]
            text = "&(" + ",".join(parts) + ")"
            songs = filter(parser.parse(text).search, self.values())
        else:
            # Regexp search
            songs = filter(parser.parse(text).search, self.values())

        if sort is None: pass
        elif callable(sort):
            songs.sort(sort)
        else:
            header = str(sort) # sanity check
            if header == "~#track": header = "album"
            elif header == "~#disc": header = "album"
            elif header == "~length": header = "~#length"
            songs = [(song(header), song) for song in songs]
            songs.sort()
            songs = [song[1] for song in songs]
        return songs

    def reload(self, song):
        self.remove(song)
        self.add(song['~filename'])

    def save(self, fn):
        util.mkdir(os.path.dirname(fn))
        f = file(fn + ".tmp", "w")
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        songs = self.values()
        for v in self.masked_files.values(): songs.extend(v.values())
        Pickle.dump(songs, f, Pickle.HIGHEST_PROTOCOL)
        f.close()
        os.rename(fn + ".tmp", fn)

    def playlists(self):
        # Return a set of playlists, normalized names.
        playlists = set()
        for song_fn in self:
            song = self[song_fn]
            for key in song:
                if key.startswith("~#playlist_"):
                    playlists.add(key[11:])
        return playlists

    def load(self, fn):
        # Load the database and read it in.
        try:
            if os.path.exists(fn):
                f = file(fn, "rb")
                try: songs = Pickle.load(f)
                except:
                    print _("W: %s is not a QL song database.") % fn
                    songs = []
                f.close()
            else: return 0, 0
        except: return 0, 0

        # Prune old entries.
        removed, changed = 0, 0
        for song in songs:
            if type(song) not in supported.values(): continue
            if song.valid():
                fn = song['~filename']
                self[fn] = song
            else:
                if song.exists():
                    fn = song['~filename']
                    changed += 1
                    song2 = MusicFile(fn)
                    if song2:
                        song2.migrate(song)
                        self[fn] = song2
                elif config.get("settings", "masked"):
                    for m in config.get("settings", "masked").split(":"):
                        if fn.startswith(m) and not os.path.ismount(m):
                            self.masked_files.setdefault(m, {})
                            self.masked_files[m][fn] = song
                            break
                    else:
                        removed += 1
        return changed, removed

    def scan(self, dirs):
        added, changed = 0, 0

        for d in dirs:
            print _("Checking %s") % d
            d = os.path.expanduser(d)
            for path, dnames, fnames in os.walk(d):
                for fn in fnames:
                    m_fn = os.path.join(path, fn)
                    if m_fn in self:
                        if self[m_fn].valid(): continue
                        else:
                            changed += 1
                            added -= 1
                    m = MusicFile(m_fn)
                    if m:
                        added += 1
                        self[m_fn] = m
                yield added, changed

    def rebuild(self, force = False):
        changed, removed = 0, 0
        for m in self.masked_files:
            if os.path.ismount(m):
                self.masked.extend(self.masked_files[m])
                del(self.masked_files[m])

        for fn in self.keys():
            if force or not self[fn].valid():
                m = MusicFile(fn)
                if m:
                    m.migrate(self[fn])
                    self[fn] = m
                    changed += 1
                else:
                    del(self[fn])
                    removed += 1

            yield changed, removed

supported = {}

def init(cache_fn = None):
    if util.check_ogg():
        print _("Enabling Ogg Vorbis support.")
        supported[".ogg"] = OggFile
    else:
        print _("W: Ogg Vorbis support is disabled! Ogg files cannot be loaded.")

    if util.check_mp3():
        print _("Enabling MP3 support.")
        supported[".mp3"] = MP3File
    else:
        print _("W: MP3 support is disabled! MP3 files cannot be loaded.")

    if util.check_flac():
        print _("Enabling FLAC support.")
        supported[".flac"] = FLACFile

    if util.check_mod():
        print _("Enabling ModPlug support.")
        for fmt in ["mod", "it", "xm", "s3m"]:
            supported["." + fmt] = ModFile

    if util.check_mpc():
        print _("Enabling Musepack support.")
        supported[".mpc"] = supported[".mp+"] = MPCFile
        
    global library
    library = Library(config.get("settings", "masked").split(":"))
    if cache_fn: library.load(cache_fn)
