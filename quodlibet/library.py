# Copyright 2004 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os, sys
import pickle, cPickle
import util; from util import escape, to
import fcntl
import random
import time
import shutil
import gettext
import config
import tempfile
import parser
import sre
import formats
from formats import MusicFile
_ = gettext.gettext

if sys.version_info < (2, 4):
    from sets import Set as set

# Remove after 0.8; migrates song databases.
# cPickle isn't new-style objects. That's stupid.
class MigrateUnpickler(pickle.Unpickler):
    TRANS = { "MPCFile":  "formats/mpc",
              "MP3File":  "formats/mp3",
              "FLACFile": "formats/flac",
              "OggFile":  "formats/oggvorbis",
              "ModFile":  "formats/mod"}

    def find_class(self, module, name):
        if (module == "library" and name in self.TRANS):
            try: return __import__(self.TRANS[name]).info
            except: pass
        elif module == "library" and name == "Unknown":
            import formats.audio
            return formats.audio.Unknown
        return pickle.Unpickler.find_class(self, module, name)

global library
library = None

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
        else: songs = filter(parser.parse(text).search, self.values())

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
        cPickle.dump(songs, f, cPickle.HIGHEST_PROTOCOL)
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
                try: songs = MigrateUnpickler(f).load()
                except:
                    print to(_("W: %s is not a QL song database.") % fn)
                    try: shutil.copy(fn, fn + ".not-valid")
                    except: pass
                    songs = []
                f.close()
            else: return 0, 0
        except: return 0, 0

        # Prune old entries.
        removed, changed = 0, 0
        for song in songs:
            if not formats.supported(song): continue
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
            print to(_("Checking %s") % d)
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

def init(cache_fn = None):
    global library
    print to(_("Supported formats:")),
    print ", ".join([os.path.basename(name) for name, mod in formats.modules
                     if mod.extensions])
    library = Library(config.get("settings", "masked").split(":"))
    if cache_fn: library.load(cache_fn)
