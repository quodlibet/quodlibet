# Copyright 2006 Joe Wreschnig
#           2011 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

"""Song library classes.

These libraries require their items to be AudioFiles, or something
close enough.
"""

from __future__ import with_statement

import os

import gobject

from quodlibet import util

from quodlibet.formats import MusicFile
from quodlibet.util.collection import Album
from quodlibet.library._library import Library, Librarian
from quodlibet.parse import Query
from quodlibet.qltk.notif import Task

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
            try: del(library._contents[song.key])
            except KeyError: pass
            else: re_add.append(library)
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

class AlbumLibrary(gobject.GObject):
    """An AlbumLibrary listens to a SongLibrary and sorts its songs into
    albums. The library behaves like a dictionary: the keys are album_keys of
    AudioFiles, the values are Album objects.
    """

    SIG_PYOBJECT = (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object,))
    __gsignals__ = {
        'changed': SIG_PYOBJECT,
        'removed': SIG_PYOBJECT,
        'added': SIG_PYOBJECT,
        }

    def __init__(self, library):
        super(AlbumLibrary, self).__init__()
        self.__albums = {}
        for key in ['get', 'keys', 'values', 'items', 'iterkeys',
                    'itervalues', 'iteritems', 'has_key']:
            setattr(self, key, getattr(self.__albums, key))

        self.library = library
        self.__loaded = False

    def __len__(self):
        return len(self.__albums)

    def __getitem__(self, key):
        return self.__albums[key]

    def __iter__(self):
        return self.__albums.itervalues()

    def refresh(self, items):
        """Refresh albums after a manual change."""
        self.emit('changed', set(items))

    def load(self):
        """Loading takes some time, and not every view needs it,
        so this must be called at least one time before using the library"""
        if not self.__loaded:
            self.__loaded = True
            self._asig = self.library.connect('added', self.__added)
            self._rsig = self.library.connect('removed', self.__removed)
            self._csig = self.library.connect('changed', self.__changed)
            self.__added(self.library, self.library.values(), signal=False)

    def destroy(self):
        if self.__loaded:
            map(self.library.disconnect, [self._asig, self._rsig, self._csig])

    def __add(self, items):
        changed = set()
        new = set()
        for song in items:
            key = song.album_key
            if key in self.__albums:
                changed.add(self.__albums[key])
            else:
                album = Album(song)
                self.__albums[key] = album
                new.add(album)
            self.__albums[key].songs.add(song)

        changed -= new

        return changed, new

    def __added(self, library, items, signal=True):
        changed, new = self.__add(items)

        for album in changed:
            album.finalize()

        if signal:
            if new: self.emit('added', new)
            if changed: self.emit('changed', changed)

    def __removed(self, library, items):
        changed = set()
        removed = set()
        for song in items:
            key = song.album_key
            album = self.__albums[key]
            album.songs.remove(song)
            changed.add(album)
            if not album.songs:
                removed.add(album)
                del self.__albums[key]

        changed -= removed

        for album in changed:
            album.finalize()

        if removed: self.emit('removed', removed)
        if changed: self.emit('changed', changed)

    def __changed(self, library, items):
        """Album keys could change between already existing ones.. so we
        have to do it the hard way and search by id."""
        changed = set()
        removed = set()
        to_add = []
        for song in items:
            # in case the key hasn't changed
            key = song.album_key
            if key in self.__albums and song in self.__albums[key].songs:
                changed.add(self.__albums[key])
            else: # key changed.. look for it in each album
                to_add.append(song)
                for key, album in self.__albums.iteritems():
                    if song in album.songs:
                        album.songs.remove(song)
                        if not album.songs:
                            removed.add(album)
                        else:
                            changed.add(album)
                        break

        # get new albums and changed ones because keys could have changed
        add_changed, new = self.__add(to_add)
        changed |= add_changed

        # check if albums that were empty at some point are still empty
        for album in removed:
            if not album.songs:
                del self.__albums[album.key]
                changed.discard(album)

        for album in changed:
            album.finalize()

        if removed: self.emit("removed", removed)
        if changed: self.emit("changed", changed)
        if new: self.emit("added", new)

class SongLibrary(Library):
    """A library for songs.

    Items in this kind of library must support (roughly) the AudioFile
    interface.
    """

    def __init__(self, *args, **kwargs):
        super(SongLibrary, self).__init__(*args, **kwargs)
        self.albums = AlbumLibrary(self)

    def destroy(self):
        super(SongLibrary, self).destroy()
        self.albums.destroy()

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
        print_d("Renaming %r to %r" % (song.key, newname), self)
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
        print_d("Loading %r." % item.key, self)
        valid = item.valid()

        # The item is fine; add it if it's not present.
        if not force and valid:
            print_d("%r is valid." % item.key, self)
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
                except (StandardError, EnvironmentError):
                    print_d("Error reloading %r." % item.key, self)
                    util.print_exc()
                    return False, True
                else:
                    print_d("Reloaded %r." % item.key, self)
                    self._contents[item.key] = item
                    return True, False
            elif not item.mounted():
                # We don't know if the item is okay or not, since
                # it's not not mounted. If the item was present
                # we need to mark it as removed.
                print_d("Masking %r." % item.key, self)
                self._masked.setdefault(item.mountpoint, {})
                self._masked[item.mountpoint][item.key] = item
                return False, present
            else:
                # The item doesn't exist at all anymore. Mark it as
                # removed if it was present, otherwise nothing.
                print_d("Ignoring (so removing) %r." % item.key, self)
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

    def rebuild(self, paths, force=False, exclude=[], cofuncid=None):
        """Reload or remove songs if they have changed or been deleted.

        This generator rebuilds the library over the course of iteration.

        Any paths given will be scanned for new files, using the 'scan'
        method.

        Only items present in the library when the rebuild is started
        will be checked.

        If this function is copooled, set "cofuncid" to enable pause/stop
        buttons in the UI.
        """

        print_d("Rebuilding, force is %s." % force, self)

        task = Task(_("Library"), _("Checking mount points"))
        if cofuncid: task.copool(cofuncid)
        for i, (point, items) in task.list(enumerate(self._masked.items())):
            if os.path.ismount(point):
                self._contents.update(items)
                del(self._masked[point])
                self.emit('added', items.values())
                yield True

        task = Task(_("Library"), _("Scanning library"))
        if cofuncid: task.copool(cofuncid)
        changed, removed = [], []
        for i, (key, item) in task.list(enumerate(sorted(self.items()))):
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
                yield True
        print_d("Removing %d, changing %d." % (len(removed), len(changed)),
                self)
        if removed:
            self.emit('removed', removed)
        if changed:
            self.emit('changed', changed)

        for value in self.scan(paths, exclude, cofuncid):
            yield value

    def add_filename(self, filename, add=True):
        """Add a file based on its filename.

        Subclasses must override this to open the file correctly.
        """
        raise NotImplementedError

    def scan(self, paths, exclude=[], cofuncid=None):
        added = []
        exclude = [util.expanduser(path) for path in exclude if path]
        for fullpath in paths:
            print_d("Scanning %r." % fullpath, self)
            desc = _("Scanning %s") % (util.unexpand(util.fsdecode(fullpath)))
            with Task(_("Library"), desc) as task:
                if cofuncid: task.copool(cofuncid)
                fullpath = util.expanduser(fullpath)
                if filter(fullpath.startswith, exclude):
                    continue
                for path, dnames, fnames in os.walk(util.fsnative(fullpath)):
                    for filename in fnames:
                        fullfilename = os.path.join(path, filename)
                        if filter(fullfilename.startswith, exclude):
                            continue
                        if fullfilename not in self._contents:
                            fullfilename = os.path.realpath(fullfilename)
                            if filter(fullfilename.startswith, exclude):
                                continue
                            if fullfilename not in self._contents:
                                item = self.add_filename(fullfilename, False)
                                if item is not None:
                                    added.append(item)
                                    if len(added) > 20:
                                        self.add(added)
                                        added = []
                                        task.pulse()
                                        yield True
                    if added:
                        self.add(added)
                        added = []
                        task.pulse()
                        yield True

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
        print_d("Unmasking %r." % point, self)
        items = self._masked.pop(point, {})
        if items:
            self.add(items.values())

    def mask(self, point):
        print_d("Masking %r." % point, self)
        removed = {}
        for item in self.itervalues():
            if item.mountpoint == point:
                removed[item.key] = item
        if removed:
            self.remove(removed.values())
        self._masked.setdefault(point, {}).update(removed)

class SongFileLibrary(SongLibrary, FileLibrary):
    """A library containing song files."""

    def add_filename(self, filename, add=True):
        """Add a song to the library based on filename.

        If 'add' is true, the song will be added and the 'added' signal
        may be fired.

        Example (add=False):
            load many songs and call Library.add(songs) to add all in one go.

        The song is returned if it is in the library after this call.
        Otherwise, None is returned.
        """

        song = None
        if filename not in self._contents:
            song = MusicFile(filename)
            if song and add:
                self.add([song])
        else:
            print_d("Already got file %r." % filename)
            song = self._contents[filename]

        return song
