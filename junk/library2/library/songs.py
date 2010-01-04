# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

"""Song library classes.

These libraries require their items to be AudioFiles, or something
close enough.
"""

import os
import traceback

from library._library import Library, Librarian

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
            library.changed([song])

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

class FileLibrary(Library):
    """A library containing items on a local(-ish) filesystem.

    These must support the valid, exists, mounted, invalidate,
    and reload methods, and have a mountpoint attribute.
    """

    def _load(self, item):
        # Check to see if the item is still on the filesystem, and
        # if it's mtime has changed.
        if item.valid():
            self._contents[item.key] = item
            return False, False
        elif item.exists():
            try:
                item.reload()
            except StandardError:
                traceback.print_exc()
                return False, True
            else:
                self._contents[item.key] = item
                return True, False
        elif not item.mounted():
            self._masked.setdefault(item.mountpoint, {})
            self._masked[item.mountpoint][item.key] = item
            return False, False
        else:
            return False, False

    def reload(self, item, changed=None, removed=None):
        """Reload a song, possibly noting its status.

        This function invalidates the song, then reloads it.
        """
        item.invalidate()
        del(self._contents[item.key])
        was_changed, was_removed = self._load(item)
        if was_changed and changed is not None:
            changed.append(item)
        elif was_removed and removed is not None:
            removed.append(item)

    def rebuild(self, force=False):
        """Reload or remove songs if they have changed or been deleted.

        If force is true, reload even unchanged songs.

        This function is an iterator that progressively yields lists
        of (changed, removed) songs.

        The 'removed' signal may fire for this library. The 'changed'
        signal may fire for this library and any other library
        sharing its songs available to its librarian.
        """
        changed, removed = [], []
        for i, (key, item) in enumerate(sorted(self.iteritems())):
            if force or not item.valid():
                self.reload(item, changed, removed)
            if not (i & 7):
                yield changed, removed
        yield changed, removed
        removed = filter(lambda item: item not in self, removed)
        if removed:
            self.remove(removed)
        if self.librarian and self in self.librarian.libraries.itervalues():
            if changed:
                self.librarian.changed(changed)
        else:
            changed = filter(self.__contains__, changed)
            if changed:
                self.changed(changed)

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
                        if fullfilename not in self:
                            item = self.add_filename(fullfilename, False)
                            if item is not None:
                                added.append(item)
                yield added

        added = filter(lambda item: item not in self, added)
        if added:
            self.add(added)

class SongFileLibrary(SongLibrary, FileLibrary):
    """A library containing song files."""

    def add_filename(self, filename, signal=True):
        """Add a song to the library based on filename.

        If 'signal' is true, the 'added' signal may fire.

        If the song was added, it is returned. Otherwise, None
        is returned.
        """
        try:
            # FIXME: Move this back out to the global scope when this
            # is merged into Quod Libet.
            from formats import MusicFile
            if filename not in self._contents:
                song = MusicFile(filename)
                if song:
                    self._contents[song.key] = song
                    if signal:
                        self.add([song])
                    return song
        except StandardError:
            traceback.print_exc()
