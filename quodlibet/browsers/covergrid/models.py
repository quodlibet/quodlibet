# Copyright 2022 Thomas Leberbauer
#           2022 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from collections.abc import Callable
from gi.repository import GObject, Gio

from quodlibet import _, app, util
from quodlibet.library.song import SongLibrary
from quodlibet.qltk.models import ObjectModelSort, ObjectStore, ObjectModelFilter
from quodlibet.util.collection import Album
from quodlibet.util.i18n import numeric_phrase
from quodlibet.util.library import background_filter


class AlbumListItem(GObject.Object):
    """This model represents an entry for a specific album.

    It will load the album cover and generate the album label on demand.
    """

    def __init__(self, album: Album | None = None):
        super().__init__()
        self._album = album
        self._cover = None
        self._label = None

        self.connect("notify::album", self._album_changed)

    def load_cover(self, size: int, cancelable: Gio.Cancellable | None = None):
        def callback(cover):
            self._cover = cover
            self.notify("cover")

        manager = app.cover_manager
        # Skip this during testing
        if manager:
            manager.get_pixbuf_many_async(
                self._album.songs, size, size, cancelable, callback
            )

    def format_label(self, pattern):
        self._label = pattern % self._album
        self.notify("label")

    def _album_changed(self, model, prop):
        self._label = None

    @GObject.Property
    def album(self):
        return self._album

    @GObject.Property
    def cover(self):
        return self._cover

    @GObject.Property
    def label(self):
        return self._label


class AlbumListCountItem(AlbumListItem):
    """This model represents an entry for a set of albums.

    It will generate a label containing the number of albums on demand.
    """

    def load_cover(self, *args, **kwargs):
        self.notify("cover")

    def format_label(self, pattern=None):
        n = self.__n_albums
        title = util.bold(_("All Albums"))
        number_phrase = numeric_phrase("%d album", "%d albums", n)
        self._label = f"{title}\n{number_phrase}"
        self.notify("label")

    @GObject.Property
    def n_albums(self):
        return self.__n_albums

    @n_albums.setter  # type: ignore
    def n_albums(self, value):
        self.__n_albums = value
        self.format_label()


class AlbumListModel(ObjectStore):
    """This model creates entries for albums from a library.

    The first entry represents the whole set of albums in the library.
    """

    def __init__(self, library: SongLibrary):
        super().__init__()
        self.__library = library

        albums = library.albums
        self.__sigs = [
            albums.connect("added", self._add_albums),
            albums.connect("removed", self._remove_albums),
            albums.connect("changed", self._change_albums),
        ]

        self.append(row=[AlbumListCountItem()])
        self.append_many(AlbumListItem(a) for a in albums.values())

    def destroy(self):
        albums = self.__library.albums
        for sig in self.__sigs:
            albums.disconnect(sig)
        self.__library = None
        self.clear()

    def _add_albums(self, library, added):
        self.append_many(AlbumListItem(a) for a in added)

    def _remove_albums(self, library, removed):
        removed_albums = removed.copy()
        iters_remove = []
        for iter_, item in self.iterrows():
            album = item.album
            if album is not None and album in removed_albums:
                removed_albums.remove(album)
                iters_remove.append(iter_)
                if not removed_albums:
                    break
        for iter_ in iters_remove:
            self.remove(iter_)

    def _change_albums(self, library, changed):
        changed_albums = changed.copy()
        for iter_, item in self.iterrows():
            album = item.album
            if album is not None and album in changed_albums:
                changed_albums.remove(album)
                self.iter_changed(iter_)
                if not changed_albums:
                    break


class AlbumListFilterModel(GObject.Object, Gio.ListModel):
    """This model filters entries in a child model.

    The property "include_item_all" toggles visibility of the first entry of the
    child model.

    The property "filter" is a function which defines visibility for all
    remaining entries of the child model. If "filter" is set to None, all
    entries are visible.
    """

    __item_all: AlbumListItem
    __include_item_all: bool
    __filter: Callable[[AlbumListItem], bool] | None = None

    def __init__(self, child_model=None, include_item_all=True, **kwargs):
        super().__init__(**kwargs)

        self.__include_item_all = include_item_all

        self._model = model = ObjectModelFilter(child_model=child_model)
        self.__item_all = self._get_item(0)
        self._update_n_albums()

        # Tell the tree model that all nodes are visible, otherwise it does not
        # emit the "row-changed" signal.
        for row in model:
            model.ref_node(row.iter)

        model.set_visible_func(self._apply_filter)
        self.__sigs = [
            model.connect("row-changed", self._row_changed),
            model.connect("row-inserted", self._row_inserted),
            model.connect("row-deleted", self._row_deleted),
            model.connect("rows-reordered", self._rows_reordered),
        ]

    def destroy(self):
        model = self._model
        for sig in self.__sigs:
            model.disconnect(sig)
        self._model = None

    @GObject.Property
    def include_item_all(self):
        return self.__include_item_all

    @include_item_all.setter  # type: ignore
    def include_item_all(self, value):
        if self.__include_item_all == value:
            return
        self.__include_item_all = value
        removed, added = (0, 1) if value else (1, 0)
        self.items_changed(0, removed, added)

    @GObject.Property
    def filter(self):
        return self.__filter

    @filter.setter  # type: ignore
    def filter(self, value):
        b = background_filter()
        if b is None and value is None:
            f = None
        elif b is None:

            def f(item):
                return value(item.album)
        else:

            def f(item):
                return b(item.album) and value(item.album)

        if f or self.__filter:
            self.__filter = f
            self._model.refilter()

    def do_get_n_items(self):
        return len(self)

    def do_get_item(self, index):
        return self[index]

    def do_get_item_type(self):
        return AlbumListItem

    def __len__(self):
        n = len(self._model)
        if self.__include_item_all or n < 1:
            return n
        return n - 1

    def __getitem__(self, index):
        if not self.__include_item_all:
            index += 1
        return self._get_item(index)

    def _get_item(self, index: int) -> AlbumListItem | None:
        model = self._model
        iter = model.iter_nth_child(None, index)
        return model.get_value(iter) if iter else None

    def _update_n_albums(self):
        self.__item_all.props.n_albums = len(self._model) - 1

    def _apply_filter(self, model, iter, _):
        filter = self.__filter
        if filter is None:
            return True
        item = model.get_value(iter)
        if item is self.__item_all:
            return True
        return filter(item)

    def _row_changed(self, model, path, iter):
        item = model.get_value(iter)
        item.notify("album")

    def _row_inserted(self, model, path, iter):
        # Ensure that the tree model will emit the "row-changed" signal
        model.ref_node(iter)

        index = path.get_indices()[0]
        if not self.__include_item_all:
            index -= 1
        if index >= 0:
            self.items_changed(index, 0, 1)
            self._update_n_albums()

    def _row_deleted(self, model, path):
        index = path.get_indices()[0]
        if not self.__include_item_all:
            index -= 1
        if index >= 0:
            self.items_changed(index, 1, 0)
            self._update_n_albums()

    def _rows_reordered(self, model, path, iter, new_order):
        n = len(self)
        self.items_changed(0, n, n)


class AlbumListSortModel(ObjectModelSort):
    """This model sorts entries of a child model"""


class CollectionListItem(GObject.Object):
    """This model represents an entry for a collection (grouping of albums).

    It will load a collection cover and generate the collection label on demand.
    """

    def __init__(self, collection_name: str = ""):
        super().__init__()
        self.collection_name = collection_name
        self._cover = None
        self._label = None
        self._cover_path = None

    def set_cover_path(self, path: str):
        """Set the path to the collection cover image"""
        from gi.repository import GdkPixbuf
        try:
            self._cover = GdkPixbuf.Pixbuf.new_from_file(path)
            self.notify("cover")
        except Exception:
            # If cover fails to load, use None (will show default)
            self._cover = None

    def load_cover(self, size: int, cancelable: Gio.Cancellable | None = None):
        """Load cover at specified size (compatibility with AlbumWidget)"""
        if self._cover_path:
            from gi.repository import GdkPixbuf
            try:
                self._cover = GdkPixbuf.Pixbuf.new_from_file_at_size(
                    self._cover_path, size, size
                )
                self.notify("cover")
            except Exception:
                self._cover = None
        else:
            self.notify("cover")

    def format_label(self):
        """Format the label for this collection"""
        self._label = util.bold(self.collection_name)
        self.notify("label")

    @GObject.Property
    def album(self):
        """Compatibility property (collections don't have albums)"""
        return None

    @GObject.Property
    def cover(self):
        return self._cover

    @GObject.Property
    def label(self):
        return self._label
