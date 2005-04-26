# Copyright 2004 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os, sys
import cPickle
import util; from util import escape, to
import fcntl
import random
import time
import shutil
import config
import tempfile
import parser
import sre
import formats
from formats import MusicFile

if sys.version_info < (2, 4):
    from sets import Set as set

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
        keys = {}
        first = {}
        all = {}
        total = len(songs)
        self.__songs = songs

        for song in songs:
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
            for song in self.__songs:
                cantoo = song.can_change()
                if can is True: can = cantoo
                elif cantoo is True: pass
                else: can = set(can) | set(cantoo)
        else:
            if not self.__songs: return False
            can = min([song.can_change(k) for song in self.__songs])
        return can

class Library(dict):
    def __init__(self, initial={}):
        self.__masked_files = {}
        dict.__init__(self, initial)

    def mask(self, mountp):
        mountd = mountp + "/"
        files = [f for f in self if f.startswith(mountd)]
        if files:
            self.__masked_files[mountp] = {}
            for f in files:
                self.__masked_files[mountp][f] = self[f]
                del(self[f])

    def unmask(self, mountp):
        if mountp in self.__masked_files:
            self.update(self.__masked_files[mountp])
            del(self.__masked_files[mountp])

    def random(self, tag):
        songs = set()
        for song in self.values(): songs.update(song.list(tag))
        if songs: return random.choice(list(songs))
        else: return None

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

    def query(self, text, sort=None):
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

    def save(self, fn):
        util.mkdir(os.path.dirname(fn))
        f = file(fn + ".tmp", "w")
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        songs = self.values()
        for v in self.__masked_files.values(): songs.extend(v.values())
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
                try: songs = cPickle.load(f)
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
            if song.valid(): self[song["~filename"]] = song
            else:
                if song.exists():
                    try: song.reload()
                    except: removed += 1
                    else:
                        self[song["~filename"]] = song
                        changed += 1
                elif config.get("settings", "masked"):
                    fn = song["~filename"]
                    for m in config.get("settings", "masked").split(":"):
                        if fn.startswith(m) and not os.path.ismount(m):
                            self.__masked_files.setdefault(m, {})
                            self.__masked_files[m][fn] = song
                            break
                    else: removed += 1
        return changed, removed

    def scan(self, dirs):
        if config.get("settings", "masked"):
            for m in config.get("settings", "masked").split(":"):
                if not os.path.ismount(m): self.mask(m)
                else: self.unmask(m)

        added, changed, removed = [], [], []

        for d in dirs:
            print to(_("Checking %s") % d)
            d = os.path.expanduser(d)
            for path, dnames, fnames in os.walk(d):
                for fn in fnames:
                    m_fn = os.path.join(path, fn)
                    if m_fn in self:
                        if not self[m_fn].valid():
                            try: self[m_fn].reload()
                            except:
                                self[m_fn]["~filename"] = m_fn
                                removed.append(self[m_fn])
                                del(self[m_fn])
                            else: changed.append(self[m_fn])
                    elif self.add(m_fn):
                        added.append(self[m_fn])
                yield added, changed, removed

    def rebuild(self, force=False):
        if config.get("settings", "masked"):
            for m in config.get("settings", "masked").split(":"):
                if not os.path.ismount(m): self.mask(m)
                else: self.unmask(m)

        changed, removed = [], []

        for fn in self.keys():
            if force or not self[fn].valid():
                try: self[fn].reload()
                except:
                    # guarantee at least a filename key even in songs
                    # that are totally gone.
                    self[fn]["~filename"] = fn
                    removed.append(self[fn])
                    del(self[fn])
                else: changed.append(self[fn])
            yield changed, removed

def init(cache_fn=None):
    global library
    print to(_("Supported formats:")),
    print ", ".join([os.path.basename(name) for name, mod in formats.modules
                     if mod.extensions])
    library = Library()
    if cache_fn: library.load(cache_fn)
    return library

