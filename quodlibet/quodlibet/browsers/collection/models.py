# -*- coding: utf-8 -*-
# Copyright 2010, 2012-2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import util
from quodlibet import config
from quodlibet import _
from quodlibet.pattern import XMLFromPattern
from quodlibet.qltk.models import ObjectTreeStore, ObjectModelFilter
from quodlibet.qltk.models import ObjectModelSort
from quodlibet.compat import iteritems, string_types, itervalues


EMPTY = _("Songs not in an album")
ALBUM_PATTERN = r"""
\<b\><album|<album>|%s>\</b\><date| \<small\>(<date>)\</small\>>
\<small\><~discs|<~discs> - ><~tracks> - <~long-length>\</small\>""" % EMPTY
ALBUM_PATTERN = ALBUM_PATTERN.lstrip()
PAT = XMLFromPattern(ALBUM_PATTERN)

UNKNOWN_PATTERN = "<b><i>%s</i></b>" % _("Unknown %s")
MULTI_PATTERN = "<b><i>%s</i></b>" % _("Multiple %s Values")
COUNT_PATTERN = " <span size='small' color='#777'>(%s)</span>"


class AlbumNode(object):

    def __init__(self, album):
        self.album = album
        self.scanned = False

    @property
    def COVER_SIZE(self):
        size = config.getint("browsers", "cover_size")
        if size <= 0:
            size = 48
        return size

    def scan_cover(self, scale_factor=1):
        if self.scanned or not self.album.songs:
            return
        self.scanned = True

        from quodlibet import app
        s = self.COVER_SIZE * scale_factor * 0.5
        self.cover = app.cover_manager.get_pixbuf_many(self.album.songs, s, s)


UnknownNode = object()
MultiNode = object()
_ORDERING = {t: (x + 1) for x, t in enumerate([MultiNode, UnknownNode, None])}
"""The ordering score by instance of singleton / "special" values"."""


def build_tree(tags, albums, cache=None):
    if not tags:
        return list(albums)
    tag, merge = tags[0]
    tree = {}
    cache = cache or {}
    for album in albums:
        cache_key = (album, tag)
        if cache_key not in cache:
            cache[cache_key] = album.list(tag)
        values = cache[cache_key]
        if merge and len(values) > 1:
            values = [MultiNode]
        for value in values or [UnknownNode]:
            tree.setdefault(value, []).append(album)
    for key, value in iteritems(tree):
        tree[key] = build_tree(tags[1:], value, cache)
    return tree


class CollectionModelMixin(object):

    def get_path_for_album(self, album):
        """Returns the path for an album or None"""

        def func(model, path, iter_, result):
            item = model.get_value(iter_)
            if getattr(item, "album", None) is album:
                # pygobject bug: treepath only valid in callback,
                # so make a copy
                result[0] = path.copy()
                return True
            return False

        res = [None]
        self.foreach(func, res)
        return res[0]

    def get_albums_for_path(self, path):
        return self.get_albums_for_iter(self.get_iter(path))

    def get_albums_for_iter(self, iter_):
        obj = self.get_value(iter_)

        if isinstance(obj, AlbumNode):
            return {obj.album}

        albums = set()
        for child_iter, value in self.iterrows(iter_):
            if isinstance(value, AlbumNode):
                albums.add(value.album)
            else:
                albums.update(self.get_albums_for_iter(child_iter))
        return albums

    def iter_albums(self, iter_):
        """Yields all albums below iter_"""

        for child_iter, value in self.iterrows(iter_):
            if isinstance(value, AlbumNode):
                yield value.album
            else:
                for album in self.iter_albums(child_iter):
                    yield album

    def get_markup(self, tags, iter_):
        obj = self.get_value(iter_, 0)
        if isinstance(obj, AlbumNode):
            return PAT % obj.album

        if isinstance(obj, string_types):
            markup = util.escape(obj)
        else:
            tag = util.tag(tags[len(self.get_path(iter_).get_indices()) - 1])
            if obj is UnknownNode:
                markup = UNKNOWN_PATTERN % util.escape(tag)
            else:
                markup = MULTI_PATTERN % util.escape(tag)

        num = len(self.get_albums_for_iter(iter_))
        return markup + COUNT_PATTERN % num

    def get_album(self, iter_):
        obj = self.get_value(iter_, 0)
        if isinstance(obj, AlbumNode):
            return obj.album


class CollectionFilterModel(ObjectModelFilter, CollectionModelMixin):
    pass


class CollectionSortModel(ObjectModelSort, CollectionModelMixin):
    pass


class CollectionTreeStore(ObjectTreeStore, CollectionModelMixin):
    def __init__(self):
        super(CollectionTreeStore, self).__init__(object)
        self.__tags = []

    def set_albums(self, tags, albums):
        self.clear()
        self.__tags = tags
        self.add_albums(albums)

    @property
    def tags(self):
        return [t[0] for t in self.__tags]

    def add_albums(self, albums):
        def _add(tree, iter_=None):
            # lowest level, add albums
            if isinstance(tree, list):
                for album in tree:
                    self.append(parent=iter_, row=[AlbumNode(album)])
                return

            # move into existing nodes and remove them from tree
            child = self.iter_children(iter_)
            while child:
                obj = self[child][0]
                if obj in tree:
                    _add(tree[obj], child)
                    del tree[obj]
                child = self.iter_next(child)

            # add missing ones
            for key, value in iteritems(tree):
                _add(value, self.append(parent=iter_, row=[key]))

        _add(build_tree(self.__tags, albums))

    def remove_albums(self, albums):
        # We can't get anything from the albums (they have no songs),
        # so we have to look through everything.

        def _remove_albums(albums, iter_=None):
            child = self.iter_children(iter_)
            while child:
                _remove_albums(albums, child)
                obj = self[child][0]
                if isinstance(obj, AlbumNode):
                    # remove albums
                    if obj.album in albums:
                        if not self.remove(child):
                            child = None
                        continue
                    else:
                        child = self.iter_next(child)
                else:
                    # clean up empty containers
                    if not self.iter_has_child(child):
                        if not self.remove(child):
                            child = None
                        continue
                    else:
                        child = self.iter_next(child)

        _remove_albums(set(albums))

    def change_albums(self, albums):
        def _check_albums(tree, iter_=None, not_found=None):
            if not_found is None:
                not_found = set()

            if isinstance(tree, list):
                # save nodes that are not there anymore
                child = self.iter_children(iter_)
                while child:
                    row = self[child]
                    try:
                        tree.remove(row[0].album)
                    except ValueError:
                        pass
                    else:
                        # it's still in the same position, trigger a redraw
                        self.row_changed(row.path, row.iter)
                    child = self.iter_next(child)
                not_found.update(tree)
                return not_found

            child = self.iter_children(iter_)
            while child:
                obj = self[child][0]
                if obj in tree:
                    _check_albums(tree[obj], child, not_found)
                    del tree[obj]
                child = self.iter_next(child)

            # everything left over changed
            def _get_all(sub, found=None):
                if found is None:
                    found = set()
                if isinstance(sub, list):
                    found.update(sub)
                    return found
                for v in itervalues(sub):
                    _get_all(v, found)
                return found
            not_found.update(_get_all(tree))

            return not_found

        not_found = _check_albums(build_tree(self.__tags, albums))
        self.remove_albums(not_found)
        self.add_albums(not_found)
