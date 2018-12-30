# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from senf import fsnative

from tests.plugin import PluginTestCase

from quodlibet import config
from quodlibet.formats import AudioFile


SONGS = [
    AudioFile({
        "title": "one",
        "artist": "piman",
        "~filename": fsnative(u"/dev/null"),
    }),
    AudioFile({
        "title": u"\xf6\xe4\xfc",
        "~filename": fsnative(u"/dev/zero"),
    }),
    AudioFile({
        "title": "three",
        "artist": "boris",
        "~filename": fsnative(u"/bin/ls"),
    }),
]

for song in SONGS:
    song.sanitize()


class THTMLExport(PluginTestCase):
    def setUp(self):
        config.init()
        self.mod = self.modules["Export to HTML"]
        self.to_html = self.mod.to_html

    def test_empty_export(self):
        text = self.to_html([])
        self.failUnless("<html" in text)

    def test_export(self):
        text = self.to_html(SONGS)
        self.failUnless(u"\xf6\xe4\xfc" in text)

    def tearDown(self):
        config.quit()
