# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

"""Base library classes.

These classes are the most basic library classes. As such they are the
least useful but most content-agnostic.
"""

import cPickle as pickle
import itertools
import os
import shutil
import threading

import gobject

# Windows doesn't have fcntl, just don't lock for now
try:
    import fcntl
except ImportError:
    fcntl = None

from quodlibet import util, print_d, print_w
from quodlibet.qltk.msg import ErrorMessage

class Library(gobject.GObject):
    """A Library contains useful objects.

    The only required method these objects support is a .key
    attribute, but specific types of libraries may require more
    advanced interfaces.
    """

    SIG_PYOBJECT = (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object,))
    __gsignals__ = {
        'changed': SIG_PYOBJECT,
        'removed': SIG_PYOBJECT,
        'added': SIG_PYOBJECT,
        }
    del(SIG_PYOBJECT)

    librarian = None
    dirty = False
    filename = None

    def __init__(self, name=None):
        super(Library, self).__init__()
        self._save_lock = threading.Lock()
        self._contents = {}
        self._masked = {}
        self._name = name
        for key in ['get', 'keys', 'values', 'items', 'iterkeys',
                    'itervalues', 'iteritems', 'has_key']:
            setattr(self, key, getattr(self._contents, key))
        if self.librarian is not None and name is not None:
            self.librarian.register(self, name)

    def destroy(self):
        if self.librarian is not None and self._name is not None:
            self.librarian._unregister(self, self._name)

    def add(self, items):
        """Add items. This causes an 'added' signal.

        Return the list of items actually added, filtering out items
        already in the library.
        """
        items = filter(lambda item: item not in self, items)
        if not items:
            return

        print_d("Adding %d items." % len(items), self)
        for item in items:
            self._contents[item.key] = item

        self.dirty = True
        self.emit('added', items)
        return items

    def remove(self, items):
        """Remove items. This causes a 'removed' signal."""
        if not items:
            return

        print_d("Removing %d items." % len(items), self)
        for item in items:
            del(self._contents[item.key])

        self.dirty = True
        self.emit('removed', items)

    def changed(self, items):
        """Alert other users that these items have changed.

        This causes a 'changed' signal. If a librarian is available
        this function will call its changed method instead, and all
        libraries that librarian manages may fire a 'changed' signal.

        The item list may be filtered to those items actually in the
        library. If a librarian is available, it will handle the
        filtering instead. That means if this method is delegated to
        the librarian, this library's changed signal may not fire, but
        another's might.
        """
        if not items:
            return
        if self.librarian and self in self.librarian.libraries.itervalues():
            print_d("Changing %d items via librarian." % len(items), self)
            self.librarian.changed(items)
        else:
            items = filter(self.__contains__, items)
            if not items:
                return
            print_d("Changing %d items directly." % len(items), self)
            self._changed(items)

    def _changed(self, items):
        # Called by the changed method and Librarians.
        if not items:
            return
        print_d("Changing %d items." % len(items), self)
        self.dirty = True
        self.emit('changed', items)

    def __iter__(self):
        """Iterate over the items in the library."""
        return self._contents.itervalues()

    def __len__(self):
        """The number of items in the library."""
        return len(self._contents)

    def __getitem__(self, key):
        """Find a item given its key."""
        return self._contents[key]

    def __contains__(self, item):
        """Check if a key or item is in the library."""
        try: return item in self._contents or item.key in self._contents
        except AttributeError: return False

    def load(self, filename, skip=False):
        """Load a library from a file, containing a picked list.

        Loading does not cause added, changed, or removed signals.
        """
        self.filename = filename
        print_d("Loading contents of %r." % filename, self)
        try:
            if os.path.exists(filename):
                # pickle makes 1000 read syscalls for 6000 songs
                # read the file into memory so that there are less
                # context switches. saves 40% here..
                fileobj = file(filename, "rb")
                try: items = pickle.loads(fileobj.read())
                except (pickle.PickleError, EnvironmentError,
                        ImportError, EOFError):
                    util.print_exc()
                    try: shutil.copy(filename, filename + ".not-valid")
                    except EnvironmentError:
                        util.print_exc()
                    items = []
                fileobj.close()
            else: return
        except EnvironmentError:
            return

        if skip:
            for item in filter(skip, items):
                self._contents[item.key] = item
        else:
            map(self._load, items)
        print_d("Done loading contents of %r." % filename, self)

    def _load(self, item):
        """Load a item. Return (changed, removed)."""
        # Subclases should override this if they want to check
        # item validity; see FileLibrary.
        print_d("Loading %r." % item.key, self)
        self.dirty = True
        self._contents[item.key] = item

    def save(self, filename=None):
        """Save the library to the given filename."""
        self._save_lock.acquire()
        if filename is None:
            filename = self.filename
        print_d("Saving contents to %r." % filename, self)
        if not os.path.isdir(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
        # Issue 479. Catch problem early
        if os.path.isdir(filename):
            msg = _("Cannot save library contents to %s (it's a directory). "
                    "Please remove it and try again.") % filename
            print_w(msg)
            # TODO: Better handling of this edge-case...
            ErrorMessage(None, _("Library Error"), msg).run()
            self._save_lock.release()
            return
        fileobj = file(filename + ".tmp", "wb")
        if fcntl is not None:
            fcntl.flock(fileobj.fileno(), fcntl.LOCK_EX)
        items = self.values()
        for masked in self._masked.values():
            items.extend(masked.values())
        # Item keys are often based on filenames, in which case
        # sorting takes advantage of the filesystem cache when we
        # reload/rescan the files.
        items.sort(key=lambda item: item.key)
        # While protocol 2 is usually faster it uses __setitem__
        # for unpickle and we override it to clear the sort cache.
        # This roundtrip makes it much slower, so we use protocol 1
        # unpickle numbers (py2.7):
        #   2: 0.66s / 2 + __set_item__: 1.18s / 1 + __set_item__: 0.72s
        # see: http://bugs.python.org/issue826897
        pickle.dump(items, fileobj, 1)
        fileobj.flush()
        os.fsync(fileobj.fileno())
        fileobj.close()
        if os.name == "nt":
            try: os.remove(filename)
            except EnvironmentError: pass
        os.rename(filename + ".tmp", filename)
        self.dirty = False
        print_d("Done saving contents to %r." % filename, self)
        self._save_lock.release()

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
            try: return library[key]
            except KeyError: pass
        else: raise KeyError, key

    def get(self, key, default=None):
        try: return self[key]
        except KeyError: return default

    def remove(self, items):
        """Remove items from all libraries."""
        for library in self.libraries.itervalues():
            library.remove(filter(library.__contains__, items))

    def __contains__(self, item):
        """Check if a key or item is in the library."""
        for library in self.libraries.itervalues():
            if item in library:
                return True
        else: return False

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

