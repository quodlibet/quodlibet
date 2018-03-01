# -*- coding: utf-8 -*-
# Copyright 2013 Simonas Kazlauskas
#      2014-2018 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from itertools import chain

from gi.repository import GObject

from quodlibet.plugins import PluginManager, PluginHandler
from quodlibet.util.cover import built_in
from quodlibet.util import print_d
from quodlibet.util.thread import call_async
from quodlibet.util.thumbnails import get_thumbnail_from_file
from quodlibet.plugins.cover import CoverSourcePlugin


class CoverPluginHandler(PluginHandler):
    """A plugin handler for CoverSourcePlugin implementation"""

    def __init__(self, use_built_in=True):
        self.providers = set()
        if use_built_in:
            self.built_in = {built_in.EmbeddedCover, built_in.FilesystemCover}
        else:
            self.built_in = set()

    def plugin_handle(self, plugin):
        return issubclass(plugin.cls, CoverSourcePlugin)

    def plugin_enable(self, plugin):
        self.providers.add(plugin)
        print_d("Registered {0} cover source".format(plugin.cls.__name__))

    def plugin_disable(self, plugin):
        self.providers.remove(plugin)
        print_d("Unregistered {0} cover source".format(plugin.cls.__name__))

    @property
    def sources(self):
        """Yields all active CoverSourcePlugin classes sorted by priority"""

        sources = chain((p.cls for p in self.providers), self.built_in)
        for p in sorted(sources, reverse=True, key=lambda x: x.priority()):
            yield p


class CoverManager(GObject.Object):

    __gsignals__ = {
        # artwork_changed([AudioFile]), emitted if the cover art for one
        # or more songs might have changed
        'cover-changed': (GObject.SignalFlags.RUN_LAST, None, (object,)),
    }

    plugin_handler = None

    def __init__(self, use_built_in=True):
        super(CoverManager, self).__init__()
        self.plugin_handler = CoverPluginHandler(use_built_in)

    def init_plugins(self):
        """Register the cover sources plugin handler with the global
        plugin manager.
        """

        PluginManager.instance.register_handler(self.plugin_handler)

    @property
    def sources(self):
        return self.plugin_handler.sources

    def cover_changed(self, songs):
        """Notify the world that the artwork for some songs or collections
        containing that songs might have changed (For example a new image was
        added to the folder or a new embedded image was added)

        This will invalidate all caches and will notify others that they have
        to re-fetch the cover and do a display update.
        """

        self.emit("cover-changed", songs)

    def acquire_cover(self, callback, cancellable, song):
        """
        Try to get covers from all cover sources until a cover is found.

        * callback(found, result) is the function which will be called when
        this method completes its job.
        * cancellable – Gio.Cancellable which will interrupt the search.
        The callback won't be called when the operation is cancelled.
        """
        sources = self.sources

        def success(source, result):
            name = source.__class__.__name__
            print_d('Successfully got cover from {0}'.format(name))
            source.disconnect_by_func(success)
            source.disconnect_by_func(failure)
            if not cancellable or not cancellable.is_cancelled():
                callback(True, result)

        def failure(source, msg):
            name = source.__class__.__name__
            print_d("Didn't get cover from {0}: {1}".format(name, msg))
            source.disconnect_by_func(success)
            source.disconnect_by_func(failure)
            if not cancellable or not cancellable.is_cancelled():
                run()

        def run():
            try:
                provider = next(sources)(song, cancellable)
            except StopIteration:
                return callback(False, None)  # No cover found

            cover = provider.cover
            if cover:
                name = provider.__class__.__name__
                print_d('Found local cover from {0}: {1}'.format(name, cover))
                callback(True, cover)
            else:
                provider.connect('fetch-success', success)
                provider.connect('fetch-failure', failure)
                provider.fetch_cover()
        if not cancellable or not cancellable.is_cancelled():
            run()

    def acquire_cover_sync(self, song, embedded=True, external=True):
        """Gets *cached* cover synchronously.

        As CoverSource fetching functionality is asynchronous it is only
        possible to check for already fetched cover.
        """

        return self.acquire_cover_sync_many([song], embedded, external)

    def acquire_cover_sync_many(self, songs, embedded=True, external=True):
        """Same as acquire_cover_sync but returns a cover for multiple
        images"""

        for plugin in self.sources:
            if not embedded and plugin.embedded:
                continue
            if not external and not plugin.embedded:
                continue

            groups = {}
            for song in songs:
                group = plugin.group_by(song) or ''
                groups.setdefault(group, []).append(song)

            # sort both groups and songs by key, so we always get
            # the same result for the same set of songs
            for key, group in sorted(groups.items()):
                song = sorted(group, key=lambda s: s.key)[0]
                cover = plugin(song).cover
                if cover:
                    return cover

    def get_cover(self, song):
        """Returns a cover file object for one song or None.

        Compared to acquire_cover_sync() this respects the prefer_embedded
        setting.
        """

        return self.get_cover_many([song])

    def get_cover_many(self, songs):
        """Returns a cover file object for many songs or None.

        Returns the first found image for a group of songs.
        It tries to return the same cover for the same set of songs.
        """

        return self.acquire_cover_sync_many(songs)

    def get_pixbuf_many(self, songs, width, height):
        """Returns a Pixbuf which fits into the boundary defined by width
        and height or None.

        Uses the thumbnail cache if possible.
        """

        fileobj = self.get_cover_many(songs)
        if fileobj is None:
            return

        return get_thumbnail_from_file(fileobj, (width, height))

    def get_pixbuf(self, song, width, height):
        """see get_pixbuf_many()"""

        return self.get_pixbuf_many([song], width, height)

    def get_pixbuf_many_async(self, songs, width, height, cancel, callback):
        """Async variant; callback gets called with a pixbuf or not called
        in case of an error. cancel is a Gio.Cancellable.

        The callback will be called in the main loop.
        """

        fileobj = self.get_cover_many(songs)
        if fileobj is None:
            return

        call_async(get_thumbnail_from_file, cancel, callback,
                   args=(fileobj, (width, height)))

    def search_cover(self, callback, cancellable, songs):
        """Search for all the covers applicable to `songs` across all providers
        Every successful image result initiates a callback
        (unless cancelled)."""

        def search_complete(source, results):
            name = source.__class__.__name__
            if not results:
                print_d('No covers from {0}'.format(name))
                return

            print_d('Successfully found covers from {0}'.format(name))
            # provider.disconnect_by_func(success)
            if not (cancellable and cancellable.is_cancelled()):
                covers = {CoverData(url=res['cover'], source=name,
                                    dimensions=res.get('dimensions', None))
                          for res in results}
                callback(source, covers)

        def failure(source, result):
            name = source.__class__.__name__
            print_d('Failed to get cover from {0}'.format(name))
            # source.disconnect_by_func(failure)

        for plugin in self.sources:
            if plugin.embedded:
                continue
            groups = {}
            for song in songs:
                group = plugin.group_by(song) or ''
                groups.setdefault(group, []).append(song)

            for key, group in sorted(groups.items()):
                song = sorted(group, key=lambda s: s.key)[0]
                provider = plugin(song)
                provider.connect('search-complete', search_complete)
                provider.search()


class CoverData(GObject.GObject):
    """Structured data for results from cover searching"""
    def __init__(self, url, source=None, dimensions=None):
        super().__init__()
        self.url = url
        self.dimensions = dimensions
        self.source = source

    def __repr__(self):
        return "CoverData<url=%s>" % self.url
