# Copyright 2013 Simonas Kazlauskas
#      2014-2025 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from itertools import chain
from typing import IO
from collections.abc import Iterable

from gi.repository import GObject, GdkPixbuf, Soup

from quodlibet import _
from quodlibet.formats import AudioFile
from quodlibet.plugins import PluginManager, PluginHandler
from quodlibet.qltk.notif import Task
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
        print_d("Registered cover source", context=plugin.cls.__name__)

    def plugin_disable(self, plugin):
        self.providers.remove(plugin)
        print_d("Unregistered cover source", context=plugin.cls.__name__)

    @property
    def sources(self):
        """Yields all active CoverSourcePlugin classes sorted by priority"""

        sources = chain((p.cls for p in self.providers), self.built_in)
        yield from sorted(sources, reverse=True, key=lambda x: x.priority())


class CoverManager(GObject.Object):
    __gsignals__ = {
        # ([AudioFile]), emitted if the cover for any songs might have changed
        "cover-changed": (GObject.SignalFlags.RUN_LAST, None, (object,)),
        # Covers were found for the songs
        "covers-found": (GObject.SignalFlags.RUN_LAST, None, (object, object)),
        # All searches were submitted, and success by provider is sent
        "searches-complete": (GObject.SignalFlags.RUN_LAST, None, (object,)),
    }

    plugin_handler = None

    def __init__(self, use_built_in=True):
        super().__init__()
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
            name = type(source).__name__
            print_d("Successfully got cover", context=name)
            source.disconnect_by_func(success)
            source.disconnect_by_func(failure)
            if not cancellable or not cancellable.is_cancelled():
                callback(True, result)

        def failure(source: GObject, msg: Soup.Message, log: bool = True) -> None:
            name = type(source).__name__
            if log:
                print_d(f"Didn't get cover: {msg}", context=name)
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
                name = type(provider).__name__
                key = song.key if song else None
                print_d(f"Found local cover for {key}", context=name)
                callback(True, cover)
            else:
                provider.connect("fetch-success", success)
                provider.connect("fetch-failure", failure)
                provider.fetch_cover()
            return None

        if not cancellable or not cancellable.is_cancelled():
            run()

    def acquire_cover_sync(self, song, embedded=True, external=True):
        """Gets *cached* cover synchronously.

        As CoverSource fetching functionality is asynchronous,
        it is only possible to check for already fetched cover.
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
                group = plugin.group_by(song) or ""
                groups.setdefault(group, []).append(song)

            # sort both groups and songs by key, so we always get
            # the same result for the same set of songs
            for _key, group in sorted(groups.items()):
                song = sorted(group, key=lambda s: s.key)[0]
                cover = plugin(song).cover
                if cover:
                    return cover
        return None

    def get_cover(self, song) -> IO | None:
        """Returns a cover file object for one song or None.

        Compared to ``acquire_cover_sync()``,
        this respects the ``prefer_embedded`` setting.
        """

        return self.get_cover_many([song])

    def get_cover_many(self, songs: Iterable[AudioFile]) -> IO | None:
        """Returns a cover file object for many songs or None.

        Returns the first found image for a group of songs.
        It tries to return the same cover for the same set of songs.
        """

        return self.acquire_cover_sync_many(songs)

    def get_pixbuf_many(
        self, songs: Iterable[AudioFile], width: int, height: int
    ) -> GdkPixbuf:
        """Returns a Pixbuf which fits into the boundary defined by width
        and height or None.

        Uses the thumbnail cache if possible.
        """

        fileobj = self.get_cover_many(songs)
        if fileobj is None:
            return None

        return get_thumbnail_from_file(fileobj, (width, height))

    def get_pixbuf(self, song: AudioFile, width: int, height: int) -> GdkPixbuf:
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

        call_async(
            get_thumbnail_from_file, cancel, callback, args=(fileobj, (width, height))
        )

    def search_cover(self, cancellable, songs):
        """Search for all the covers applicable to `songs` across all providers
        Every successful image result emits a 'covers-found' signal
        (unless cancelled)."""

        sources = [source for source in self.sources if not source.embedded]
        processed = {}
        all_groups = {}
        task = Task(
            _("Cover Art"), _("Querying album art providers"), stop=cancellable.cancel
        )

        def finished(provider, success):
            processed[provider] = success
            total = self._total_groupings(all_groups)

            frac = len(processed) / total
            print_d(f"Got result for {provider} ({len(processed)} / {total} group(s))")
            task.update(frac)
            if frac >= 1:
                task.finish()
                self.emit("searches-complete", processed)

        def search_complete(provider, results):
            name = provider.name
            if not results:
                print_d(f"No covers from {name}")
                finished(provider, False)
                return
            finished(provider, True)
            if not (cancellable and cancellable.is_cancelled()):
                covers = {
                    CoverData(
                        url=res["cover"],
                        source=name,
                        dimensions=res.get("dimensions", None),
                    )
                    for res in results
                }
                self.emit("covers-found", provider, covers)
            provider.disconnect_by_func(search_complete)

        def failure(provider: CoverManager, message: str, log: bool = True):
            finished(provider, False)
            name = provider.__class__.__name__
            if log:
                print_d(f"Failed to get cover ({message})", context=name)
            provider.disconnect_by_func(failure)

        def song_groups(songs, sources):
            all_groups = {}
            for plugin in sources:
                groups = {}
                for song in songs:
                    group = plugin.group_by(song) or ""
                    groups.setdefault(group, []).append(song)
                all_groups[plugin] = groups
            return all_groups

        all_groups = song_groups(songs, sources)
        print_d(f"Got {self._total_groupings(all_groups)} plugin groupings")

        for plugin_cls, groups in all_groups.items():
            for key, group in sorted(groups.items()):
                song = sorted(group, key=lambda s: s.key)[0]
                artists = {s.comma("artist") for s in group}
                if len(artists) > 1:
                    print_d(
                        f"{len(artists)} artist groups in {key} "
                        "- probably a compilation. "
                        "Using provider to search for compilation"
                    )
                    song = AudioFile(song)
                    try:
                        del song["artist"]
                    except KeyError:
                        # Artist(s) from other grouped songs, never mind.
                        pass
                provider = plugin_cls(song)
                provider.connect("search-complete", search_complete)
                provider.connect("fetch-failure", failure)
                provider.search()
        return all_groups

    def _total_groupings(self, groups):
        return sum(len(g) for g in groups.values())


class CoverData(GObject.GObject):
    """Structured data for results from cover searching"""

    def __init__(self, url, source=None, dimensions=None):
        super().__init__()
        self.url = url
        self.dimensions = dimensions
        self.source = source

    def __repr__(self):
        return f"CoverData<url={self.url} @ {self.dimensions}>"
