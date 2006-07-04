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
        """Rename the song in all libraries it belongs to."""
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
        for song in self.values():
            tags.update(song.list(tag))
        return list(tags)

    def rename(self, song, newname):
        """Rename a song.

        This requires a special method because it can change the
        song's key.
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
        item.invalidate()
        was_changed, was_removed = self._load(item)
        if was_changed and changed is not None:
            changed.append(item)
        elif was_removed and removed is not None:
            removed.append(item)

    def rebuild(self, force=False):
        changed, removed = []
        for i, (key, item) in enumerate(sorted(self.iteritems())):
            if force or not item.valid():
                self.reload(item, changed, removed)
            if not (i & 7):
                yield changed, removed
        yield changed, removed
        removed = filter(lambda item: item not in self, removed)
        if removed:
            self.removed(removed)
        if self.librarian and self in self.librarian.libraries.itervalues():
            if changed:
                self.librarian.changed(changed)
        else:
            changed = filter(self.__contains__, changed)
            if changed:
                self.changed(changed)

    def scan(self, paths):
        added = []
        for point, items in self._masked.items():
            if os.path.ismount(point):
                self._contents.update(items)
                added.extend(items.values())
                del(self._masked[point])
                yield added

        # FIXME: This is a port of the old code. It should use URIs
        # rather than filenames.
        for path in directories:
            fullpath = os.path.expanduser(path)
            for path, dnames, fnames in os.walk(path):
                for filename in fnames:
                    fullfilename = os.path.join(path, filename)
                    if fullfilename not in self._contents:
                        fullfilename = os.path.realpath(fullfilename)
                        if fullfilename not in self:
                            if self.add_filename(fullfilename):
                                added.append(self[fullfilename])
                yield added

        added = filter(lambda item: item not in self, added)
        if added:
            self.add(added)

class SongFileLibrary(SongLibrary, FileLibrary):
    """A library containing song files."""
