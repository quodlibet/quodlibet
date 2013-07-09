# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

from tests import add
from tests.plugin import PluginTestCase

from quodlibet import config
from quodlibet import util
from quodlibet.formats._audio import AudioFile


SONGS = [
    AudioFile({"title": "one", "artist": "piman", "~filename": "/dev/null"}),
    AudioFile({"title": u"\xf6\xe4\xfc", "~filename": "/dev/zero"}),
    AudioFile({"title": "three", "artist": "boris", "~filename": "/bin/ls"})
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
        self.failUnless(u"\xf6\xe4\xfc".encode("utf-8") in text)

    def tearDown(self):
        config.quit()

add(THTMLExport)
