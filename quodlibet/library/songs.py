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

import gobject

from formats import MusicFile
from library._library import Library, Librarian
from parse import Query

class SongLibrarian(Librarian):
    """A librarian for SongLibraries."""

    def tag_values(self, tag):
        """Return a list of all values for the given tag."""
        tags = set()
        for library in self.libraries.itervalues():
            tags.update(library.tag_values(tag))
        return list(tags)

    def rename(self, song, newname):
        """Rename the song in all libraries it belongs to.

        The 'changed' signal will fire for any library the song is in.
        """
        # This needs to poke around inside the library directly.  If
        # it uses add/remove to handle the songs it fires incorrect
        # signals. If it uses the library's rename method, it breaks
        # the call for future libraries because the item's key has
        # changed. So, it needs to reimplement the method.
        re_add = []
        for library in self.libraries.itervalues():
            if song.key in library:
                del(library._contents[song.key])
                re_add.append(library)
        song.rename(newname)
        for library in re_add:
            library._contents[song.key] = song
            library._changed([song])

    def reload(self, item):
        """Reload a song.

        Unlike SongLibrary#reload, this function does not append to
        lists and always emits signals. This is because a caller
        wanting the list semantics wouldn't know where to send the
        appropriate signals.
        """
        to_add = []
        for library in self.libraries.itervalues():
            try: del(library._contents[item.key])
            except KeyError: pass
            else: to_add = []
        try: library = to_add[0]
        except IndexError: return
        was_changed, was_removed = library._load(item)
        if was_removed:
            for library in to_add:
                library.emit('removed', [item])
        elif was_changed:
            for library in to_add:
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

    def rename(self, song, newname):
        """Rename a song.

        This requires a special method because it can change the
        song's key.

        The 'changed' signal may fire for this library.

        If the song exists in multiple libraries you cannot use this
        method. Instead, use the librarian.
        """
        del(self._contents[song.key])
        song.rename(newname)
        self._contents[song.key] = song
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

    __update_id = None

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

    def rebuild(self, force=False):
        """Reload or remove songs if they have changed or been deleted.

        If force is true, reload even unchanged songs.

        This function is an iterator that progressively yields lists
        of (changed, removed) songs.

        The 'removed' signal may fire for this library. The 'changed'
        signal may fire for this library and any other library
        sharing its songs available to its librarian.
        """
        if self.__update_id is not None:
            gobject.source_remove(self.__update_id)
            self.__update_id = None
        changed, removed = [], []
        for i, (key, item) in enumerate(sorted(self.iteritems())):
            if force or not item.valid():
                self.reload(item, changed, removed)
            if not (i & 7):
                yield changed, removed
        yield changed, removed
        if removed:
            self.emit('removed', removed)
        if changed:
            self.changed(changed)

    def update_in_background(self, paths):
        """Reload or remove songs if they have changed or been deleted.

        This function sets up GObject main loop idle handlers to
        rebuild the library and will do so over the course of several
        iterations of it. Starting a rebuild while the previous one is
        running will stop the running one.

        Any filenames given will be scanned for new files.

        Only items present in the library when the rebuild is started
        will be checked.
        """
        if self.__update_id is not None:
            gobject.source_remove(self.__update_id)
            self.__update_id = None
        next = self.__update_in_background_real(paths).next
        self.__update_id = gobject.idle_add(
            next, priority=gobject.PRIORITY_LOW)
    def __update_in_background_real(self, paths):
        for point, items in self._masked.items():
            if os.path.ismount(point):
                self._contents.update(items)
                del(self._masked[point])
                self.emit('added', items.values())
                yield True

        changed, removed = [], []
        for i, (key, item) in enumerate(sorted(self.items())):
            if key in self._contents and not item.valid():
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
                yield True
        if removed:
            self.emit('removed', removed)
        if changed:
            self.emit('changed', changed)

        added = []
        for fullpath in paths:
            fullpath = os.path.expanduser(fullpath)
            for i, (path, dnames, fnames) in enumerate(os.walk(fullpath)):
                for filename in fnames:
                    fullfilename = os.path.join(path, filename)
                    fullfilename = os.path.realpath(fullfilename)
                    if fullfilename not in self._contents:
                        item = self.add_filename(fullfilename, False)
                        if item is not None:
                            added.append(item)
                            if len(added) > 5:
                                yield True
                if added:
                    self.emit('added', added)
                    added = []
                yield True
        if added:
            self.emit('added', added)

        self.__update_id = None
        yield False

    def add_filename(self, filename, signal=True):
        """Add a file based on its filename.

        Subclasses must override this to open the file correctly.
        """
        raise NotImplementedError

    def scan(self, paths):
        """Scan filesystem paths and add files.

        This function is an iterator that progressively yields a list
        of added songs.

        This function does not update or remove files, only add
        them. To update or remove files, use the rebuild method.
        It may also unmask songs, 'adding' them.

        The 'added' signal may be fired for this library.

        Item keys must be their filename for this method to work.
        FIXME: Maybe this should be URIs instead.
        """

        if self.__update_id is not None:
            gobject.source_remove(self.__update_id)
            self.__update_id = None

        added = []
        for point, items in self._masked.items():
            if os.path.ismount(point):
                self._contents.update(items)
                added.extend(items.values())
                del(self._masked[point])
                yield added

        for fullpath in paths:
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
                yield added

        if added:
            self.emit('added', added)

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
