# Copyright 2006 Joe Wreschnig
#           2012 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

"""
Librarians for libraries.
"""

import gobject
import itertools
from quodlibet.util.dprint import print_d


class Librarian(gobject.GObject):
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

    def destroy(self):
        pass

    def register(self, library, name):
        """Register a library with this librarian."""
        if name in self.libraries or name in self.__signals:
            raise ValueError("library %r is already active" % name)

        added_sig = library.connect('added', self.__added)
        removed_sig = library.connect('removed', self.__removed)
        changed_sig = library.connect('changed', self.__changed)
        self.libraries[name] = library
        self.__signals[library] = [added_sig, removed_sig, changed_sig]

    def _unregister(self, library, name):
        # This function, unlike register, should be private.
        # Libraries get unregistered at the discretion of the
        # librarian, not the libraries.
        del(self.libraries[name])
        map(library.disconnect, self.__signals[library])
        del(self.__signals[library])

    # FIXME: We can be smarter about this -- queue a list of items
    # and fire the signal after a short wait, to take advantage of
    # a case where many libraries fire a signal at the same time (or
    # one fires a signal often).

    def __changed(self, library, items):
        self.emit('changed', items)

    def __added(self, library, items):
        self.emit('added', items)

    def __removed(self, library, items):
        self.emit('removed', items)

    def changed(self, items):
        """Triage the items and inform their real libraries."""
        for library in self.libraries.itervalues():
            in_library = filter(library.__contains__, items)
            if in_library:
                library._changed(in_library)

    def __getitem__(self, key):
        """Find a item given its key."""
        for library in self.libraries.itervalues():
            try:
                return library[key]
            except KeyError:
                pass
        else:
            raise KeyError(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def remove(self, items):
        """Remove items from all libraries."""
        for library in self.libraries.itervalues():
            library.remove(filter(library.__contains__, items))

    def __contains__(self, item):
        """Check if a key or item is in the library."""
        for library in self.libraries.itervalues():
            if item in library:
                return True
        else:
            return False

    def __iter__(self):
        """Iterate over all items in all libraries."""
        return itertools.chain(*self.libraries.itervalues())

    def move(self, items, from_, to):
        """Move items from one library to another.

        This causes 'removed' signals on the from library, and 'added'
        signals on the 'to' library, but will not cause any signals
        to be emitted via this librarian.
        """
        try:
            from_.handler_block(self.__signals[from_][1])
            to.handler_block(self.__signals[to][0])
            from_.remove(items)
            to.add(items)
        finally:
            from_.handler_unblock(self.__signals[from_][1])
            to.handler_unblock(self.__signals[to][0])


class SongLibrarian(Librarian):
    """A librarian for SongLibraries."""

    def tag_values(self, tag):
        """Return a list of all values for the given tag."""
        tags = set()
        for library in self.libraries.itervalues():
            tags.update(library.tag_values(tag))
        return list(tags)

    def rename(self, song, newname, changed=None):
        """Rename the song in all libraries it belongs to.

        The 'changed' signal will fire for any library the song is in.
        """
        # This needs to poke around inside the library directly.  If
        # it uses add/remove to handle the songs it fires incorrect
        # signals. If it uses the library's rename method, it breaks
        # the call for future libraries because the item's key has
        # changed. So, it needs to reimplement the method.
        re_add = []
        print_d("Renaming %r to %r" % (song.key, newname), self)
        for library in self.libraries.itervalues():
            try:
                del library._contents[song.key]
            except KeyError:
                pass
            else:
                re_add.append(library)
        song.rename(newname)
        for library in re_add:
            library._contents[song.key] = song
            if changed is None:
                library._changed([song])
            else:
                print_d("Delaying changed signal for %r." % library, self)
                changed.append(song)

    def reload(self, item, changed=None, removed=None):
        """Reload a song."""
        re_add = []
        print_d("Reloading %r" % item.key, self)
        for library in self.libraries.itervalues():
            try:
                del library._contents[item.key]
            except KeyError:
                pass
            else:
                re_add.append(library)
        try:
            library = re_add[0]
        except IndexError:
            return
        # Rely on the first library in the list to do the actual
        # load, then just inform the other libraries what happened.
        was_changed, was_removed = library._load_item(item)
        if was_removed:
            for library in re_add:
                library.emit('removed', [item])
        elif was_changed:
            for library in re_add:
                library._contents[item.key] = item
                library.emit('changed', [item])
