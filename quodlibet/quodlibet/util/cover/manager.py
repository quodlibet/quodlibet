# -*- coding: utf-8 -*-
# Copyright 2013 Simonas Kazlauskas
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from itertools import chain

from quodlibet.plugins import PluginManager
from quodlibet.util.cover import built_in
from quodlibet.plugins.cover import CoverSourcePlugin


class CoverPluginHandler(object):
    def __init__(self):
        self.providers = set()
        self.built_in = set([built_in.EmbedCover, built_in.FilesystemCover])

    def init_plugins(self):
        PluginManager.instance.register_handler(self)

    def plugin_handle(self, plugin):
        if not issubclass(plugin.cls, CoverSourcePlugin):
            return False

        plugin._hander = self
        self.providers.add(plugin)
        print_d("Registered {0} cover source".format(plugin.cls.__name__))
        # We do not want plugin to be exposed and managed by PluginManager.
        # We just use all available sources instead.
        return False

    @property
    def sources(self):
        sources = chain((p.cls for p in self.providers), self.built_in)
        for p in sorted(sources, reverse=True, key=lambda x: x.priority()):
            yield p

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
            if not cancellable.is_cancelled():
                callback(True, result)

        def failure(source, msg):
            name = source.__class__.__name__
            print_d("Didn't get cover from {0}: {1}".format(name, msg))
            source.disconnect_by_func(success)
            source.disconnect_by_func(failure)
            if not cancellable.is_cancelled():
                run()

        def run():
            try:
                provider = next(sources)(song, cancellable)
            except StopIteration:
                return callback(False, None)  # No cover found

            cover = provider.cover
            if cover:
                name = provider.__class__.__name__
                print_d('Found local cover from {0}'.format(name))
                callback(True, cover)
            else:
                provider.connect('fetch-success', success)
                provider.connect('fetch-failure', failure)
                provider.fetch_cover()
        run()

    def acquire_cover_sync(self, song):
        """
        Gets *cached* cover synchronously. As CoverSource fetching
        functionality is asynchronous it is only possible to check for already
        fetched cover.
        """
        for plugin in self.sources:
            cover = plugin(song).cover
            if cover:
                return cover


cover_plugins = CoverPluginHandler()
