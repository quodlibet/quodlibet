# Copyright 2006 Joe Wreschnig
#           2011-2021 Nick Boultbee
#           2013,2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Base library classes.

These classes are the most basic library classes. As such they are the
least useful but most content-agnostic.
"""

import os
import shutil
import time
from pathlib import Path
from typing import Set, Optional, Generator
from threading import Thread
from queue import Queue

from gi.repository import GObject

from quodlibet import _
from quodlibet import formats
from quodlibet import util
from quodlibet.formats import (MusicFile, AudioFileError, load_audio_files,
                               dump_audio_files, SerializationError, AudioFile)
from quodlibet.qltk.notif import Task
from quodlibet.query import Query
from quodlibet.util.atomic import atomic_save
from quodlibet.util.collection import Album
from quodlibet.util.collections import DictMixin
from quodlibet.util.dprint import print_d, print_w
from quodlibet.util.path import unexpand, mkdir, normalize_path, ishidden, ismount
from senf import fsn2text, fsnative


class Library(GObject.GObject, DictMixin):
    """A Library contains useful objects.

    The only required method these objects support is a .key
    attribute, but specific types of libraries may require more
    advanced interfaces.

    Every method which takes a sequence of items expects items to
    implement __iter__, __len__ and __contains__.

    Likewise the signals emit sequences which implement
    __iter__, __len__ and __contains__ e.g. set(), list() or tuple().

    WARNING: The library implements the dict interface with the exception
    that iterating over it yields values and not keys.
    """

    __gsignals__ = {
        'changed': (GObject.SignalFlags.RUN_LAST, None, (object,)),
        'removed': (GObject.SignalFlags.RUN_LAST, None, (object,)),
        'added': (GObject.SignalFlags.RUN_LAST, None, (object,)),
    }

    librarian = None
    dirty = False

    def __init__(self, name=None):
        super().__init__()
        self._contents = {}
        self._name = name
        if self.librarian is not None and name is not None:
            self.librarian.register(self, name)

    def destroy(self):
        if self.librarian is not None and self._name is not None:
            self.librarian._unregister(self, self._name)

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
        if self.librarian and self in self.librarian.libraries.values():
            print_d(f"Changing {len(items)} items via librarian.", self._name)
            self.librarian.changed(items)
        else:
            items = {item for item in items if item in self}
            if not items:
                return
            print_d(f"Changing {len(items)} items directly.", self._name)
            self._changed(items)

    def _changed(self, items):
        assert isinstance(items, set)

        # Called by the changed method and Librarians.
        if not items:
            return
        print_d(f"Changing {len(items)} items.", self._name)
        self.dirty = True
        self.emit('changed', items)

    def __iter__(self):
        """Iterate over the items in the library."""
        return iter(self._contents.values())

    def iteritems(self):
        return iter(self._contents.items())

    def iterkeys(self):
        return iter(self._contents.keys())

    def itervalues(self):
        return iter(self._contents.values())

    def __len__(self):
        """The number of items in the library."""
        return len(self._contents)

    def __getitem__(self, key):
        """Find a item given its key."""
        return self._contents[key]

    def __contains__(self, item):
        """Check if a key or item is in the library."""
        try:
            return item in self._contents or item.key in self._contents
        except AttributeError:
            return False

    def get_content(self):
        """All items including hidden ones for saving the library
           (see FileLibrary with masked items)
        """

        return list(self.values())

    def keys(self):
        return self._contents.keys()

    def values(self):
        return self._contents.values()

    def _load_item(self, item):
        """Load (add) an item into this library"""
        # Subclasses should override this if they want to check
        # item validity; see `FileLibrary`.
        print_d(f"Loading {item.key!r}", self._name)
        self.dirty = True
        self._contents[item.key] = item

    def _load_init(self, items):
        """Load many items into the library (on start)"""
        # Subclasses should override this if they want to check
        # item validity; see `FileLibrary`.
        content = self._contents
        for item in items:
            content[item.key] = item

    def add(self, items):
        """Add items. This causes an 'added' signal.

        Return the sequence of items actually added, filtering out items
        already in the library.
        """

        items = {item for item in items if item not in self}
        if not items:
            return items

        print_d(f"Adding {len(items)} items.", self._name)
        for item in items:
            self._contents[item.key] = item

        self.dirty = True
        self.emit('added', items)
        return items

    def remove(self, items):
        """Remove items. This causes a 'removed' signal.

        Return the sequence of items actually removed.
        """

        items = {item for item in items if item in self}
        if not items:
            return items

        print_d(f"Removing {len(items)} items.", self._name)
        for item in items:
            del self._contents[item.key]

        self.dirty = True
        self.emit('removed', items)
        return items


def _load_items(filename):
    """Load items from disk.

    In case of an error returns default or an empty list.
    """

    try:
        with open(filename, "rb") as fp:
            data = fp.read()
    except EnvironmentError:
        print_w("Couldn't load library file from: %r" % filename)
        return []

    try:
        items = load_audio_files(data)
    except SerializationError:
        # there are too many ways this could fail
        util.print_exc()

        # move the broken file out of the way
        try:
            shutil.copy(filename, filename + ".not-valid")
        except EnvironmentError:
            util.print_exc()

        return []

    return items


class PicklingMixin:
    """A mixin to provide persistence of a library by pickling to disk"""

    filename = None

    def load(self, filename):
        """Load a library from a file, containing a picked list.

        Loading does not cause added, changed, or removed signals.
        """

        self.filename = filename
        print_d("Loading contents of %r." % filename, self)

        items = _load_items(filename)

        # this loads all items without checking their validity, but makes
        # sure that non-mounted items are masked
        self._load_init(items)

        print_d(f"Done loading contents of {filename!r}", self._name)

    def save(self, filename=None):
        """Save the library to the given filename, or the default if `None`"""

        if filename is None:
            filename = self.filename

        print_d(f"Saving contents to {filename!r}", self._name)

        try:
            dirname = os.path.dirname(filename)
            mkdir(dirname)
            with atomic_save(filename, "wb") as fileobj:
                fileobj.write(dump_audio_files(self.get_content()))
        except SerializationError:
            # Can happen when we try to pickle while the library is being
            # modified, like in the periodic 15min save.
            # Ignore, as it should try again later or on program exit.
            util.print_exc()
        except EnvironmentError:
            print_w(f"Couldn't save library to path {filename!r}")
        else:
            self.dirty = False


class PicklingLibrary(Library, PicklingMixin):
    """A library that pickles its contents to disk"""

    def __init__(self, name=None):
        print_d("Using pickling persistence for library \"%s\"" % name)
        PicklingMixin.__init__(self)
        Library.__init__(self, name)


class AlbumLibrary(Library):
    """An AlbumLibrary listens to a SongLibrary and sorts its songs into
    albums.

    The library behaves like a dictionary: the keys are album_keys of
    AudioFiles, the values are Album objects.
    """

    def __init__(self, library):
        self.librarian = None
        print_d("Initializing Album Library to watch %r" % library._name)

        super().__init__(
            "AlbumLibrary for %s" % library._name)

        self._library = library
        self._asig = library.connect('added', self.__added)
        self._rsig = library.connect('removed', self.__removed)
        self._csig = library.connect('changed', self.__changed)
        self.__added(library, library.values(), signal=False)

    def load(self):
        # deprecated
        pass

    def destroy(self):
        for sig in [self._asig, self._rsig, self._csig]:
            self._library.disconnect(sig)

    def _get(self, item):
        return self._contents.get(item)

    def __add(self, items):
        changed = set()
        new = set()
        for song in items:
            key = song.album_key
            if key in self._contents:
                changed.add(self._contents[key])
            else:
                album = Album(song)
                self._contents[key] = album
                new.add(album)
            self._contents[key].songs.add(song)

        changed -= new
        return changed, new

    def __added(self, library, items, signal=True):
        changed, new = self.__add(items)

        for album in changed:
            album.finalize()

        if signal:
            if new:
                self.emit('added', new)
            if changed:
                self.emit('changed', changed)

    def __removed(self, library, items):
        changed = set()
        removed = set()
        for song in items:
            key = song.album_key
            album = self._contents[key]
            album.songs.remove(song)
            changed.add(album)
            if not album.songs:
                removed.add(album)
                del self._contents[key]

        changed -= removed

        for album in changed:
            album.finalize()

        if removed:
            self.emit('removed', removed)
        if changed:
            self.emit('changed', changed)

    def __changed(self, library, items):
        """Album keys could change between already existing ones.. so we
        have to do it the hard way and search by id."""
        print_d("Updating affected albums for %d items" % len(items))
        changed = set()
        removed = set()
        to_add = []
        for song in items:
            # in case the key hasn't changed
            key = song.album_key
            if key in self._contents and song in self._contents[key].songs:
                changed.add(self._contents[key])
            else:  # key changed.. look for it in each album
                to_add.append(song)
                for key, album in self._contents.items():
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
                del self._contents[album.key]
                changed.discard(album)

        for album in changed:
            album.finalize()

        if removed:
            self.emit("removed", removed)
        if changed:
            self.emit("changed", changed)
        if new:
            self.emit("added", new)


class SongLibrary(PicklingLibrary):
    """A library for songs.

    Items in this kind of library must support (roughly) the AudioFile
    interface.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @util.cached_property
    def albums(self):
        return AlbumLibrary(self)

    def destroy(self):
        super().destroy()
        if "albums" in self.__dict__:
            self.albums.destroy()

    def tag_values(self, tag):
        """Return a set of all values for the given tag."""
        return {value for song in self.values()
                for value in song.list(tag)}

    def rename(self, song, new_name, changed: Optional[Set] = None):
        """Rename a song.

        This requires a special method because it can change the
        song's key.

        The 'changed' signal may fire for this library or the changed
        song is added to the passed changed set().

        If the song exists in multiple libraries you cannot use this
        method. Instead, use the librarian.
        """
        if song.key == new_name:
            print_d(f"Nothing changed for {new_name!r}")
            return
        print_d(f"Renaming {song.key!r} to {new_name!r}", self)
        del self._contents[song.key]
        song.rename(new_name)
        self._contents[song.key] = song
        if changed is not None:
            changed.add(song)
        else:
            self.changed({song})

    def query(self, text, sort=None, star=Query.STAR):
        """Query the library and return matching songs."""
        if isinstance(text, bytes):
            text = text.decode('utf-8')

        songs = self.values()
        if text != "":
            songs = list(filter(Query(text, star).search, songs))
        return songs


def iter_paths(root, exclude=[], skip_hidden=True):
    """yields paths contained in root (symlinks dereferenced)

    Any path starting with any of the path parts included in exclude
    are ignored (before and after dereferencing symlinks)

    Directory symlinks are not followed (except root itself)

    Args:
        root (fsnative)
        exclude (List[fsnative])
        skip_hidden (bool): Ignore files which are hidden or where any
            of the parent directories are hidden.
    Yields:
        fsnative: absolute dereferenced paths
    """

    assert isinstance(root, fsnative)
    assert all((isinstance(p, fsnative) for p in exclude))
    assert os.path.abspath(root)

    def skip(path):
        if skip_hidden and ishidden(path):
            return True
        # FIXME: normalize paths..
        return any((path.startswith(p) for p in exclude))

    if skip_hidden and ishidden(root):
        return

    for path, dnames, fnames in os.walk(root):
        if skip_hidden:
            dnames[:] = list(filter(
                lambda d: not ishidden(os.path.join(path, d)), dnames))
        for filename in fnames:
            fullfilename = os.path.join(path, filename)
            if skip(fullfilename):
                continue
            fullfilename = os.path.realpath(fullfilename)
            if skip(fullfilename):
                continue
            yield fullfilename


class FileLibrary(PicklingLibrary):
    """A library containing items on a local(-ish) filesystem.

    These must support the valid, exists, mounted, and reload methods,
    and have a mountpoint attribute.
    """

    def __init__(self, name=None):
        super().__init__(name)
        self._masked = {}

    def _load_init(self, items):
        """Add many items to the library, check if the
        mountpoints are available and mark items as masked if not.

        Does not check if items are valid.
        """

        mounts = {}
        contents = self._contents
        masked = self._masked

        for item in items:
            mountpoint = item.mountpoint

            if mountpoint not in mounts:
                is_mounted = ismount(mountpoint)

                # In case mountpoint is mounted through autofs we need to
                # access a sub path for it to mount
                # https://github.com/quodlibet/quodlibet/issues/2146
                if not is_mounted:
                    item.exists()
                    is_mounted = ismount(mountpoint)

                mounts[mountpoint] = is_mounted
                # at least one not mounted, make sure masked has an entry
                if not is_mounted:
                    masked.setdefault(mountpoint, {})

            if mounts[mountpoint]:
                contents[item.key] = item
            else:
                masked[mountpoint][item.key] = item

    def _load_item(self, item, force=False):
        """Add an item, or refresh it if it's already in the library.
        No signals will be fired.
        Return a tuple of booleans: (changed, removed)
        """
        print_d(f"Loading {item.key!r}", self._name)
        valid = item.valid()

        # The item is fine; add it if it's not present.
        if not force and valid:
            print_d(f"{item.key!r} is valid.", self._name)
            self._contents[item.key] = item
            return False, False
        else:
            # Either we should force a load, or the item is not okay.
            # We're going to reload; this could change the key.  So
            # remove the item if it's currently in.
            try:
                del self._contents[item.key]
            except KeyError:
                present = False
            else:
                present = True
            # If the item still exists, reload it.
            if item.exists():
                try:
                    item.reload()
                except AudioFileError:
                    print_w(f"Error reloading {item.key!r}", self._name)
                    return False, True
                else:
                    print_d(f"Reloaded {item.key!r}.", self._name)
                    self._contents[item.key] = item
                    return True, False
            elif not item.mounted():
                # We don't know if the item is okay or not, since
                # it's not not mounted. If the item was present
                # we need to mark it as removed.
                print_d(f"Masking {item.key!r}", self._name)
                self._masked.setdefault(item.mountpoint, {})
                self._masked[item.mountpoint][item.key] = item
                return False, present
            else:
                # The item doesn't exist at all anymore. Mark it as
                # removed if it was present, otherwise nothing.
                print_d(f"Ignoring (so removing) {item.key!r}.", self._name)
                return False, present

    def reload(self, item, changed=None, removed=None):
        """Reload a song, possibly noting its status.

        If sets are given, it assumes the caller will handle signals,
        and only updates the sets. Otherwise, it handles signals
        itself. It *always* handles library contents, so do not
        try to remove (again) a song that appears in the removed set.
        """

        was_changed, was_removed = self._load_item(item, force=True)
        assert not (was_changed and was_removed)

        if was_changed:
            if changed is None:
                self.emit('changed', {item})
            else:
                changed.add(item)
        elif was_removed:
            if removed is None:
                self.emit('removed', {item})
            else:
                removed.add(item)

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

        print_d(f"Rebuilding, force is {force}", self._name)

        task = Task(_("Library"), _("Checking mount points"))
        if cofuncid:
            task.copool(cofuncid)
        for i, (point, items) in task.list(enumerate(self._masked.items())):
            if ismount(point):
                self._contents.update(items)
                del self._masked[point]
                self.emit('added', list(items.values()))
                yield True

        task = Task(_("Library"), _("Scanning library"))
        if cofuncid:
            task.copool(cofuncid)
        changed, removed = set(), set()
        for i, (key, item) in task.list(enumerate(sorted(self.items()))):
            if key in self._contents and force or not item.valid():
                self.reload(item, changed, removed)
                # These numbers are pretty empirical. We should yield more
            # often than we emit signals; that way the main loop stays
            # interactive and doesn't get bogged down in updates.
            if len(changed) >= 200:
                self.emit('changed', changed)
                changed = set()
            if len(removed) >= 200:
                self.emit('removed', removed)
                removed = set()
            if len(changed) > 20 or i % 200 == 0:
                yield True
        print_d(f"Removing {len(removed)}, changing {len(changed)}).", self._name)
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

    def contains_filename(self, filename):
        """Returns if a song for the passed filename is in the library.

        Returns:
            bool
        """

        raise NotImplementedError

    def scan(self, paths, exclude=[], cofuncid=None):

        def need_yield(last_yield=[0]):
            current = time.time()
            if abs(current - last_yield[0]) > 0.015:
                last_yield[0] = current
                return True
            return False

        def need_added(last_added=[0]):
            current = time.time()
            if abs(current - last_added[0]) > 1.0:
                last_added[0] = current
                return True
            return False

        # first scan each path for new files
        paths_to_load = Queue()
        for scan_path in paths:
            print_d(f"Scanning {scan_path}", self._name)
            desc = _("Scanning %s") % (fsn2text(unexpand(scan_path)))
            with Task(_("Library"), desc) as task:
                if cofuncid:
                    task.copool(cofuncid)

                for real_path in iter_paths(scan_path, exclude=exclude):
                    if need_yield():
                        task.pulse()
                        yield
                    # skip unknown file extensions
                    if not formats.filter(real_path):
                        continue
                    normalized = normalize_path(real_path, True)
                    # already loaded
                    if normalized in self._contents:
                        continue
                    paths_to_load.put(normalized)

        yield

        npaths_to_load = paths_to_load.qsize()
        songs = Queue()
        def worker():
            while not paths_to_load.empty():
                path = paths_to_load.get()
                song = MusicFile(path)
                songs.put(song)
        for i in range(16):
            t = Thread(target=worker)
            t.start()

        # then (try to) load all new files
        print_d("Loading files.")
        with Task(_("Library"), _("Loading files")) as task:
            if cofuncid:
                task.copool(cofuncid)

            added = []
            for i in task.gen(range(npaths_to_load)):
                # This is here just in case the final number of puts to songs
                # doesn't match the length of paths_to_load. We don't want to
                # wait forever.
                if paths_to_load.empty():
                    break
                item = songs.get()
                if item is not None:
                    added.append(item)
                    if len(added) > 100 or need_added():
                        self.add(added)
                        added = []
                        yield
                if added and need_yield():
                    yield
            if added:
                self.add(added)
                added = []
                yield True
        print_d("Files are loaded.")

    def get_content(self):
        """Return visible and masked items"""

        items = list(self.values())
        for masked in self._masked.values():
            items.extend(masked.values())

        # Item keys are often based on filenames, in which case
        # sorting takes advantage of the filesystem cache when we
        # reload/rescan the files.
        items.sort(key=lambda item: item.key)

        return items

    def masked(self, item):
        """Return true if the item is in the library but masked."""
        try:
            point = item.mountpoint
        except AttributeError:
            # Checking a key.
            for point in self._masked.values():
                if item in point:
                    return True
        else:
            # Checking a full item.
            return item in self._masked.get(point, {}).values()

    def unmask(self, point):
        print_d(f"Unmasking {point!r}", self._name)
        items = self._masked.pop(point, {})
        if items:
            self.add(items.values())

    def mask(self, point):
        print_d(f"Masking {point!r}", self._name)
        removed = {}
        for item in self.values():
            if item.mountpoint == point:
                removed[item.key] = item
        if removed:
            self.remove(removed.values())
            self._masked.setdefault(point, {}).update(removed)

    @property
    def masked_mount_points(self):
        """List of mount points that contain masked items"""

        return list(self._masked.keys())

    def get_masked(self, mount_point):
        """List of items for a mount point"""

        return list(self._masked.get(mount_point, {}).values())

    def remove_masked(self, mount_point):
        """Remove all songs for a masked point"""

        self._masked.pop(mount_point, {})

    def move_root(self, old_root: str, new_root: fsnative) \
            -> Generator[None, None, None]:
        """
        Move the root for all songs in a given (scan) directory.

        We avoid dereferencing the destination, to allow users things like:
          1. Symlink new_path -> old_root
          2. Move QL root to new_path
          3. Remove symlink
          4. Move audio files: old_root -> new_path

        """
        old_path = Path(normalize_path(old_root, canonicalise=True)).expanduser()
        new_path = Path(normalize_path(new_root)).expanduser()
        if not old_path.is_dir():
            raise ValueError(f"Source {old_path!r} is not a directory")
        if not new_path.is_dir():
            raise ValueError(f"Destination {new_path!r} is not a directory")
        print_d(f"{self._name}: checking {len(self.values())} item(s) for {old_path!r}")
        missing: Set[AudioFile] = set()
        changed = set()
        total = len(self)
        if not total:
            return
        with Task(_("Library"), _("Moving library files")) as task:
            yield
            for i, song in enumerate(list(self.values())):
                task.update(i / total)
                key = normalize_path(song.key)
                path = Path(key)
                if old_path in path.parents:
                    # TODO: more Pathlib-friendly dir replacement...
                    new_key = key.replace(str(old_path), str(new_path), 1)
                    new_key = normalize_path(new_key, canonicalise=False)
                    if new_key == key:
                        print_w(f"Substitution failed for {key!r}")
                    # We need to update ~filename and ~mountpoint
                    song.sanitize()
                    song.write()
                    if self.move_song(song, new_key):
                        changed.add(song)
                    else:
                        missing.add(song)
                elif not (i % 1000):
                    print_d(f"Not moved, for example: {key!r}")
                if not i % 100:
                    yield
            self.changed(changed)
            if missing:
                print_w(f"Couldn't find {len(list(missing))} files: {missing}")
        yield
        self.save()
        print_d(f"Done moving to {new_path!r}.")

    def move_song(self, song: AudioFile, new_path: fsnative) -> bool:
        """Updates the location of a song, without touching the file.

        :returns: True if it was could be found (and moved)
        """
        existed = True
        key = song.key
        print_d(f"Moving {key!r} -> {new_path!r}")
        try:
            del self._contents[key]
        except KeyError:
            existed = False
            # Continue - maybe it's already moved
        song.sanitize(new_path)
        self._contents[new_path] = song
        return existed


class SongFileLibrary(SongLibrary, FileLibrary):
    """A library containing song files.
    Pickles contents to disk as `FileLibrary`"""

    def __init__(self, name=None):
        print_d(f"Initializing {type(self)}: {name!r}")
        super().__init__(name)

    def contains_filename(self, filename):
        key = normalize_path(filename, True)
        return key in self._contents

    def get_filename(self, filename):
        key = normalize_path(filename, True)
        return self._contents.get(key)

    def add_filename(self, filename, add=True):
        """Add a song to the library based on filename.

        If 'add' is true, the song will be added and the 'added' signal
        may be fired.

        Example (add=False):
            load many songs and call Library.add(songs) to add all in one go.

        The song is returned if it is in the library after this call.
        Otherwise, None is returned.
        """

        key = normalize_path(filename, True)
        song = None
        if key not in self._contents:
            song = MusicFile(filename)
            if song and add:
                self.add([song])
        else:
            print_d(f"Already got file {filename!r}")
            song = self._contents[key]

        return song
