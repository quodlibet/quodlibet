# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

"""Base library classes.

These classes are the most basic library classes. As such they are the
least useful but most content-agnostic.
"""

import cPickle as pickle
import fcntl
import os
import shutil
import traceback

import gobject
import gtk

class Library(gtk.Object):
    """A Library contains useful objects.

    The only required method these objects support is a .key
    attribute, but specific types of libraries may require more
    advanced interfaces.
    """

    SIG_PYOBJECT = (gobject.SIGNAL_RUN_LAST,
    gobject.TYPE_NONE, (object,))

    __gsignals__ = {
        # Songs have changed.
        'changed': SIG_PYOBJECT,

        # Songs were removed.
        'removed': SIG_PYOBJECT,

        # Songs were added.
        'added': SIG_PYOBJECT,
        }

    librarian = None

    def __init__(self, name=None):
        super(Library, self).__init__()
        self._contents = {}
        self._masked = {}
        for key in ['get', 'keys', 'values', 'items', 'iterkeys',
                    'itervalues', 'iteritems', 'has_key']:
            setattr(self, key, getattr(self._contents, key))
        if self.librarian is not None and name is not None:
            self.librarian.register(self, name)

    def add(self, songs):
        """Add songs. This causes an 'added' signal."""
        for song in songs:
            self._contents[song.key] = song
        self.emit('added', songs)

    def remove(self, songs):
        """Remove songs. This causes a 'removed' signal."""
        for song in songs:
            del(self._contents[song.key])
        self.emit('removed', songs)

    def changed(self, songs):
        """Alert other users that these songs have changed.

        This causes a 'changed' signal.

        The song list is filtered to those songs actually in the
        library.
        """
        self.emit('changed', filter(self.__contains__, songs))

    def __iter__(self):
        """Iterate over the items in the library."""
        return self._contents.itervalues()

    def __len__(self):
        """The number of items in the library."""
        return len(self._contents)

    def __getitem__(self, key):
        """Find a song given its key."""
        return self._contents[key]

    def __contains__(self, song):
        """Check if a key or song is in the library."""
        try: return song in self._contents or song.key in self._contents
        except AttributeError: return False

    def load(self, filename):
        """Load a library from a file, containing a picked list.

        Loading does not cause added, changed, or removed signals. It
        does return a tuple of number (changed, removed).
        """
        try:
            if os.path.exists(filename):
                fileobj = file(filename, "rb")
                try: songs = pickle.load(fileobj)
                except (pickle.PickleError, EnvironmentError):
                    traceback.print_exc()
                    try: shutil.copy(filename, filename + ".not-valid")
                    except EnvironmentError:
                        traceback.print_exc()
                    songs = []
                fileobj.close()
            else:
                return 0, 0
        except EnvironmentError:
            return 0, 0

        # Prune old entries.
        removed, changed = 0, 0
        for song in songs:
            if song.key is None:
                # Most likely library corruption.
                continue
            else:
                nchanged, nremoved = self._load(song)
                changed += nchanged
                removed += nremoved

        return changed, removed

    def _load(self, song):
        """Load a song. Return (changed, removed)."""
        # Subclases should override this if they want to check
        # song validity; see FileLibrary.
        self._contents[song.key] = song
        return False, False

    def save(self, filename):
        """Save the library to the given filename."""
        if not os.path.isdir(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
        fileobj = file(filename + ".tmp", "wb")
        fcntl.flock(fileobj.fileno(), fcntl.LOCK_EX)
        songs = self.values()
        for masked in self._masked.values():
            songs.extend(masked.values())
        # Song keys are often based on filenames, in which case
        # sorting takes advantage of the filesystem cache when we
        # reload/rescan the files.
        songs.sort(key=lambda song: song.key)
        pickle.dump(songs, fileobj, pickle.HIGHEST_PROTOCOL)
        fileobj.close()
        os.rename(filename + ".tmp", filename)

    def masked(self, item):
        """Return true if the item is in the library but masked."""
        for point in self._masked:
            if item in point or item in point.itervalues():
                return True
        else: return False

class Librarian(gtk.Object):
    """The librarian is a nice interface to all active libraries.

    Librarians are a kind of meta-library. When any of their
    registered libraries fire a signal, they fire the same
    signal. Likewise, they provide various methods equivalent to the
    ones found in libraries that group the results of the real
    libraries.

    Attributes:
    libraries -- a dict mapping library names to libraries
    """

    SIG_PYOBJECT = (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object,))
    __gsignals__ = {
        'changed': SIG_PYOBJECT,
        'removed': SIG_PYOBJECT,
        'added': SIG_PYOBJECT,
        }

    def __init__(self):
        super(Librarian, self).__init__()
        self.libraries = {}
        self.__signals = {}

    def register(self, library, name):
        """Register a library with this librarian."""
        if name in self.libraries or name in self.__signals:
            raise ValueError("library %r is already active" % name)

        added_sig = library.connect('added', self.__added)
        removed_sig = library.connect('removed', self.__removed)
        changed_sig = library.connect('changed', self.__changed)
        library.connect('destroy', self.__unregister, name)
        self.libraries[name] = library
        self.__signals[name] = [added_sig, removed_sig, changed_sig]

    def __unregister(self, library, name):
        # This function, unlike register, should be private.
        # Libraries get unregistered at the discretion of the
        # librarian, not the libraries.
        del(self.libraries[name])
        del(self.__signals[name])

    # FIXME: We can be smarter about this -- queue a list of songs
    # and fire the signal after a short wait, to take advantage of
    # a case where many libraries fire a signal at the same time (or
    # one fires a signal often).

    def __changed(self, library, songs):
        self.emit('changed', songs)

    def __added(self, library, songs):
        self.emit('added', songs)

    def __removed(self, library, songs):
        self.emit('removed', songs)

    def changed(self, songs):
        """Triage the songs and inform their real libraries."""
        for library in self.libraries.itervalues():
            in_library = filter(library.__contains__, songs)
            if in_library:
                library.changed(in_library)

    def __getitem__(self, key):
        """Find a song given its key."""
        for library in self.libraries.itervalues():
            try: return library[key]
            except KeyError: pass
        else: raise KeyError, key

    def __contains__(self, song):
        """Check if a key or song is in the library."""
        for library in self.libraries.itervalues():
            if song in library:
                return True
        else: return False
