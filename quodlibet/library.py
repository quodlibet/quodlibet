# Copyright 2004 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os, sys
import cPickle as pickle
import util; from util import to
import fcntl
import random
import shutil
import formats
from formats import MusicFile
from parse import Query

if sys.version_info < (2, 4):
    from sets import Set as set

try: import formats.flac
except: pass
else: sys.modules["formats.flac_"] = formats.flac

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
            if self.shared:
                return ngettext('missing from %d song',
                                'missing from %d songs',
                                self.missing) % self.missing
            elif self.complete:
                return ngettext('different across %d song',
                                'different across %d songs',
                                self.total) % self.total
            else:
                d = ngettext('different across %d song',
                              'different across %d songs',
                              self.have) % self.have
                m = ngettext('missing from %d song',
                              'missing from %d songs',
                              self.missing) % self.missing
                return ", ".join([d, m])

        def safenicestr(self):
            if self.shared and self.complete: return str(self)
            elif self.shared:
                return "\n".join(['%s <i>(%s)</i>' % (s, self.paren())
                                  for s in str(self).split("\n")])
            else: return '<i>(%s)</i>' % self.paren()

    class SharedComment(Comment): shared = True
    class UnsharedComment(Comment): shared = False
    class PartialSharedComment(SharedComment): complete = False
    class PartialUnsharedComment(UnsharedComment): complete = False

    def realkeys(self):
        return filter(lambda s: s and "~" not in s and "=" not in s, self)

    is_file = True
    multiple_values = True

    def __init__(self, songs):
        keys = {}
        first = {}
        all = {}
        total = len(songs)
        self.__songs = songs

        for song in songs:
            self.is_file &= song.is_file
            self.multiple_values &= song.multiple_values
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

    def tag_values(self, tag):
        # Return a list of all values for the given tag.
        songs = set()
        for song in self.values(): songs.update(song.list(tag))
        return list(songs)

    def rename(self, song, newfn):
        assert song.is_file
        oldfn = song['~filename']
        song.rename(newfn)
        if oldfn in self:
            del(self[oldfn])
            self[song['~filename']] = song

    def remove(self, song):
        try: del(self[song['~filename']])
        except KeyError: pass

    def add_song(self, song):
        if song["~filename"] not in self:
            self[song["~filename"]] = song
            return song
        return False

    def add(self, fn):
        if fn not in self:
            song = MusicFile(fn)
            if song: return self.add_song(song)
            else: return False
        else: return True

    def query(self, text, sort=None, star=Query.STAR):
        if isinstance(text, str): text = text.decode('utf-8')
        if text == "": songs = self.values()
        else:
            songs = filter(Query(text, star).search, self.itervalues())

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
        # Cold cache start without sorting: 11.9 +/- 0.2s
        # Cold cache start with sorting: 10.5 +/- 0.1s
        songs = [(song.get("~filename"), song) for song in songs]
        songs.sort()
        songs = [s[1] for s in songs]
        pickle.dump(songs, f, pickle.HIGHEST_PROTOCOL)
        f.close()
        os.rename(fn + ".tmp", fn)

    def masked(self, filename):
        for v in self.__masked_files.values():
            if filename in v: return True
        return False

    def load(self, fn):
        # Load the database and read it in.
        try:
            if os.path.exists(fn):
                f = file(fn, "rb")
                try: songs = pickle.load(f)
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
            if "~filename" not in song: continue # library corruption
            elif song.is_file:
                if not formats.supported(song):
                    removed += 1
                    continue

            if isinstance(song.get("~#rating"), int):
                song["~#rating"] /= 4.0

            if song.valid(): self[song["~filename"]] = song
            elif song.exists():
                try: song.reload()
                except: removed += 1
                else:
                    self[song["~filename"]] = song
                    changed += 1
            elif not song.mounted():
                fn = song["~filename"]
                mp = song["~mountpoint"]
                self.__masked_files.setdefault(mp, {})
                self.__masked_files[mp][fn] = song
            else: removed += 1

        return changed, removed

    # Reload, mask, or remove a song, adjusting given lists as necessary.
    def reload(self, song, changed=None, removed=None):
        if changed is None: changed = []
        if removed is None: removed = []
        fn = song["~filename"]
        if song.exists():
            try: song.reload()
            except:
                song["~filename"] = fn
                self.remove(song)
                removed.append(song)
            else: changed.append(song)
        elif not song.mounted():
            mp = song["~mountpoint"]
            self.__masked_files.setdefault(mp, {})
            self.__masked_files[mp][fn] = song
            self.remove(song)
            removed.append(song)
        else:
            self.remove(song)
            removed.append(song)

    def scan(self, dirs):
        added, changed, removed = [], [], []

        for mp, songs in self.__masked_files.items():
            if os.path.ismount(mp):
                self.update(songs)
                added.extend(songs.values())
                del(self.__masked_files[mp])
                yield added, changed, removed

        for d in dirs:
            print to(_("Checking %s") % util.fsdecode(d))
            d = os.path.expanduser(d)
            for path, dnames, fnames in os.walk(d):
                # don't re-resolve this path every time
                for fn in fnames:
                    m_fn = os.path.join(path, fn)
                    if m_fn not in library:
                        m_fn = os.path.realpath(m_fn)
                        if m_fn not in self and self.add(m_fn):
                            added.append(self[m_fn])
                yield added, changed, removed

    def rebuild(self, force=False):
        changed, removed = [], []
        fns = self.keys()
        fns.sort()
        for fn in fns:
            song = self[fn]
            if force or not song.valid():
                self.reload(song, changed, removed)
            yield changed, removed

def init(cache_fn=None):
    global library
    s = ", ".join(formats.modules)
    print to(_("Supported formats: %s")) % s
    library = Library()
    if cache_fn: library.load(cache_fn)
    return library

