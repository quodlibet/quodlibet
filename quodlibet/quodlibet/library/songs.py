# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

"""Song library classes.

These libraries require their items to be AudioFiles, or something
close enough.
"""

import os
import traceback

from quodlibet import util

from quodlibet.formats import MusicFile
from quodlibet.library._library import Library, Librarian
from quodlibet.parse import Query

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
        print_d("%s: Renaming %r" % (type(self).__name__, song.key))
        for library in self.libraries.itervalues():
            try: del(library._contents[song.key])
            except KeyError: pass
            else: re_add.append(library)
        song.rename(newname)
        for library in re_add:
            library._contents[song.key] = song
            if changed is None:
                library._changed([song])
            else:
                print_d("%s: Delaying changed signal for %r." % (
                    type(self).__name__, library))
                changed.append(song)

    def reload(self, item, changed=None, removed=None):
        """Reload a song."""
        re_add = []
        print_d("%s: Reloading %r" % (type(self).__name__, item.key))
        for library in self.libraries.itervalues():
            try: del(library._contents[item.key])
            except KeyError: pass
            else: re_add.append(library)
        try: library = re_add[0]
        except IndexError: return
        # Rely on the first library in the list to do the actual
        # load, then just inform the other libraries what happened.
        was_changed, was_removed = library._load(item)
        if was_removed:
            for library in re_add:
                library.emit('removed', [item])
        elif was_changed:
            for library in re_add:
                library._contents[item.key] = item
                library.emit('changed', [item])

class SongLibrary(Library):
    """A library for songs.

    Items in this kind of library must support (roughly) the AudioFile
    interface.
    """

    def tag_values(self, tag):
        """Return a list of all values for the given tag."""
        tags = set()
        for song in self.itervalues():
            tags.update(song.list(tag))
        return list(tags)

    def rename(self, song, newname, changed=None):
        """Rename a song.

        This requires a special method because it can change the
        song's key.

        The 'changed' signal may fire for this library.

        If the song exists in multiple libraries you cannot use this
        method. Instead, use the librarian.
        """
        print_d(
            "%s: Renaming %r to %r" % (type(self).__name__, song.key, newname))
        del(self._contents[song.key])
        song.rename(newname)
        self._contents[song.key] = song
        if changed is not None:
            print_d("%s: Delaying changed signal." % (type(self).__name__))
            changed.append(song)
        else:
            self.changed([song])

    def query(self, text, sort=None, star=Query.STAR):
        """Query the library and return matching songs."""
        if isinstance(text, str): text = text.decode('utf-8')
        if text == "": songs = self.values()
        else: songs = filter(Query(text, star).search, self)
        return songs

class FileLibrary(Library):
    """A library containing items on a local(-ish) filesystem.

    These must support the valid, exists, mounted, and reload methods,
    and have a mountpoint attribute.
    """

    def _load(self, item, force=False):
        # Add an item, or refresh it if it's already in the library.
        # No signals will be fired. Return a tuple of booleans,
        # (changed, removed)
        valid = item.valid()

        # The item is fine; add it if it's not present.
        if not force and valid:
            self._contents[item.key] = item
            return False, False
        else:
            # Either we should force a load, or the item is not okay.
            # We're going to reload; this could change the key.  So
            # remove the item if it's currently in.
            try: del(self._contents[item.key])
            except KeyError: present = False
            else: present = True
            # If the item still exists, reload it.
            if item.exists():
                try:
                    item.reload()
                except StandardError:
                    traceback.print_exc()
                    return False, True
                else:
                    self._contents[item.key] = item
                    return True, False
            elif not item.mounted():
                # We don't know if the item is okay or not, since
                # it's not not mounted. If the item was present
                # we need to mark it as removed.
                self._masked.setdefault(item.mountpoint, {})
                self._masked[item.mountpoint][item.key] = item
                return False, present
            else:
                # The item doesn't exist at all anymore. Mark it as
                # removed if it was present, otherwise nothing.
                return False, present

    def reload(self, item, changed=None, removed=None):
        """Reload a song, possibly noting its status.

        If lists are given, it assumes the caller will handle signals,
        and only updates the lists. Otherwise, it handles signals
        itself. It *always* handles library contents, so do not
        try to remove (again) a song that appears in the removed list.
        """
        was_changed, was_removed = self._load(item, force=True)
        if was_changed and changed is not None:
            changed.append(item)
        elif was_removed and removed is not None:
            removed.append(item)
        elif changed is None and removed is None:
            if was_changed:
                self.changed([item])
            elif was_removed:
                self.emit('removed', [item])

    def rebuild(self, paths, progress=None, force=False):
        """Reload or remove songs if they have changed or been deleted.

        This generator rebuilds the library over the course of iteration.

        Any paths given will be scanned for new files, using the 'scan'
        method.

        Only items present in the library when the rebuild is started
        will be checked.
        """

        if progress:
            progress.show()
            progress.set_text(_("Checking mount points"))
            progress.set_fraction(0)
        frac = 1.0 / (len(self._masked) or 1)
        for i, (point, items) in enumerate(self._masked.items()):
            if os.path.ismount(point):
                self._contents.update(items)
                del(self._masked[point])
                self.emit('added', items.values())
                if progress:
                    progress.set_fraction(i * frac)
                yield True

        if progress:
            progress.set_fraction(0)
            progress.set_text(_("Scanning library"))
        changed, removed = [], []
        frac = 1.0 / (len(self) or 1)
        for i, (key, item) in enumerate(sorted(self.items())):
            if key in self._contents and force or not item.valid():
                self.reload(item, changed, removed)
            # These numbers are pretty empirical. We should yield more
            # often than we emit signals; that way the main loop stays
            # interactive and doesn't get bogged down in updates.
            if len(changed) > 100:
                self.emit('changed', changed)
                changed = []
            if len(removed) > 100:
                self.emit('removed', removed)
                removed = []
            if len(changed) > 5 or i % 100 == 0:
                if progress:
                    progress.set_fraction(i * frac)
                yield True
        if removed:
            self.emit('removed', removed)
        if changed:
            self.emit('changed', changed)

        for value in self.scan(paths, progress):
            yield value
        if progress:
            progress.hide()

    def add_filename(self, filename, signal=True):
        """Add a file based on its filename.

        Subclasses must override this to open the file correctly.
        """
        raise NotImplementedError

    def scan(self, paths, progress=None):
        if progress:
            progress.show()
        added = []
        for fullpath in paths:
            if progress:
                progress.set_text(_("Scanning %s") % (
                    util.unexpand(util.fsdecode(fullpath))))
            fullpath = os.path.expanduser(fullpath)
            for path, dnames, fnames in os.walk(fullpath):
                for filename in fnames:
                    fullfilename = os.path.join(path, filename)
                    if fullfilename not in self._contents:
                        fullfilename = os.path.realpath(fullfilename)
                        if fullfilename not in self._contents:
                            item = self.add_filename(fullfilename, False)
                            if item is not None:
                                added.append(item)                
                                if len(added) > 5:
                                    self.emit('added', added)
                                    added = []
                                    if progress:
                                        progress.pulse()
                                    yield True
                if progress:
                    progress.pulse()
                yield True
        if added:
            self.emit('added', added)
        if progress:
            progress.hide()

    def masked(self, item):
        """Return true if the item is in the library but masked."""
        try: point = item.mountpoint
        except AttributeError:
            # Checking a key.
            for point in self._masked.itervalues():
                if item in point:
                    return True
        else:
            # Checking a full item.
            return item in self._masked.get(point, {}).itervalues()

    def unmask(self, point):
        items = self._masked.pop(point, {})
        if items:
            self.add(items.values())

    def mask(self, point):
        removed = {}
        for item in self.itervalues():
            if item.mountpoint == point:
                removed[item.key] = item
        if removed:
            self.remove(removed.values())
        self._masked.setdefault(point, {}).update(removed)

class SongFileLibrary(SongLibrary, FileLibrary):
    """A library containing song files."""

    def add_filename(self, filename, signal=True):
        """Add a song to the library based on filename.

        If 'signal' is true, the 'added' signal may fire.

        If the song was added, it is returned. Otherwise, None
        is returned.
        """
        try:
            if filename not in self._contents:
                song = MusicFile(filename)
                if song:
                    self._contents[song.key] = song
                    if signal:
                        self.add([song])
                    return song
        except StandardError:
            traceback.print_exc()
