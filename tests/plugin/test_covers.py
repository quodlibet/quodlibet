# Copyright 2012 Christoph Reiter
#           2023 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import gi

from tests import run_gtk_loop

FORMAT_HEADERS = (b"\x89PNG", b"\xFF\xD8\xFF", b"GIF")

gi.require_version("Soup", "3.0")
from gi.repository import Gtk

from dataclasses import dataclass, field
from time import time, sleep
from typing import Any

import pytest as pytest

from quodlibet.formats import AudioFile
from quodlibet.util.cover.http import ApiCoverSourcePlugin
from senf import fsnative
from tests.plugin import PluginTestCase, plugins

AN_ARTIST = "The Beatles"
AN_ALBUM = "Let It Be"
A_SONG = AudioFile({"album": AN_ALBUM, "artist": AN_ARTIST})
AN_MBID = "82a4adf2-008b-3236-bb7a-bd93d7ed9677"


def delay_rerun(self, *args):
    # Try to recover from any network blips
    sleep(10)
    return True


class TCovers(PluginTestCase):
    def setUp(self) -> None:
        self.song = A_SONG
        self.blank_song = AudioFile()

    def test_cover_path_lastfm(self):
        plugin_cls = self.plugins["lastfm-cover"].cls
        assert isinstance(plugin_cls(self.song).cover_path, fsnative)
        assert isinstance(plugin_cls(self.blank_song).cover_path, fsnative)

    def test_cover_path_musicbrainz(self):
        plugin_cls = self.plugins["musicbrainz-cover"].cls
        assert isinstance(plugin_cls(self.song).cover_path, fsnative)
        assert isinstance(plugin_cls(self.blank_song).cover_path, fsnative)

    def test_cover_path_discogs(self):
        plugin_cls = self.plugins["discogs-cover"].cls
        assert isinstance(plugin_cls(self.song).cover_path, fsnative)
        assert isinstance(plugin_cls(self.blank_song).cover_path, fsnative)


@dataclass
class Results:
    covers: list[Any] = field(default_factory=list)
    success: bool | None = None


@pytest.mark.network
@pytest.mark.flaky(max_runs=3, min_passes=1, rerun_filter=delay_rerun)
@pytest.mark.parametrize("plugin_class_name",
                         ["lastfm-cover", "discogs-cover", "musicbrainz-cover"])
def test_live_cover_download(plugin_class_name):
    if plugin_class_name == "musicbrainz-cover":
        pytest.skip("https://coverartarchive.org is currently broken")

    results = Results()
    # Just in case overhanging events
    run_gtk_loop()

    def search_complete(source, data, results):
        results.covers = data

    def good(source, data, results):
        results.success = True
        header = data.read(4)
        data.close()
        assert any(header.startswith(f)
                   for f in FORMAT_HEADERS), f"Unknown format: {header}"

    def bad(source, error, results):
        # For debugging
        results.covers = error
        results.success = False

    plugin_cls = plugins[plugin_class_name].cls
    song = A_SONG
    if "musicbrainz" in plugin_class_name:
        song["musicbrainz_albumid"] = AN_MBID
    plugin: ApiCoverSourcePlugin = plugin_cls(song)

    sig = plugin.connect("search-complete", search_complete, results)
    sig2 = plugin.connect("fetch-success", good, results)
    sig3 = plugin.connect("fetch-failure", bad, results)
    try:
        start = time()
        if "musicbrainz" in plugin_class_name:
            # Isn't called by fetch_cover()
            plugin.search()
        plugin.fetch_cover()
        while time() - start < 10 and results.success is None:
            Gtk.main_iteration_do(False)

        assert results.success is not None, "No signal triggered"
        assert results.success, f"Didn't succeed: {results.covers}"
        covers = results.covers
        assert covers, "Didn't get search results"
        first = covers[0]
        assert first["cover"].startswith("http")
        assert "dimensions" in first
        if "album" in first:
            # Only lastfm populates this currently
            assert first["album"] == AN_ALBUM, f"Downloaded wrong cover: {covers}"
    finally:
        plugin.disconnect(sig)
        plugin.disconnect(sig2)
        plugin.disconnect(sig3)
