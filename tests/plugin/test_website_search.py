# Copyright 2018 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet.formats import AudioFile
from quodlibet.pattern import Pattern
from tests.plugin import PluginTestCase
from quodlibet import config

A_SONG = AudioFile(
    {
        "title": "foo",
        "artist": "barman",
        "~filename": "/tmp/dir/barman - foo.mp3",
        "website": "https://example.com",
    }
)


class TWebsiteSearch(PluginTestCase):
    def setUp(self):
        self.mod = self.modules["Website Search"]

    def test_full(self):
        plugin = self.mod.WebsiteSearch()
        plugin.chosen_site = True
        plugin._no_launch = True
        assert plugin.plugin_songs([A_SONG])

    def test_website_for(self):
        song = A_SONG
        pat = Pattern("https://example.com/<artist>/<title>")

        url = self.mod.website_for(pat, song)
        assert url == "https://example.com/barman/foo"

    def test_website_for_dirname(self):
        song = AudioFile(A_SONG)
        pat = Pattern("https://example.com/<~dirname>")
        url = self.mod.website_for(pat, song)
        # This is probably what the user wanted, ish
        assert url == "https://example.com//tmp/dir"

    def test_website_for_website(self):
        song = AudioFile(A_SONG)
        pat = Pattern("<website>")
        url = self.mod.website_for(pat, song)
        assert url == "https://example.com"

    def tearDown(self):
        config.quit()
