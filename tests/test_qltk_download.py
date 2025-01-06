# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import config
from quodlibet.formats import AudioFile
from quodlibet.formats.remote import RemoteFile
from quodlibet.qltk.download import DownloadProgress
from tests import TestCase, mkdtemp, run_gtk_loop


def an_rf(i: int) -> AudioFile:
    return RemoteFile(f"https://github.com/quodlibet/quodlibet/{i}.mp3")


class TDownloadProgress(TestCase):
    def setUp(self):
        config.init()

    def tearDown(self):
        config.quit()

    def test_download_fails_for_non_existent(self):
        songs = [an_rf(i) for i in range(3)]
        d = DownloadProgress(songs)
        for _ in d.download_songs(mkdtemp()):
            run_gtk_loop()
        assert d.failed == set(songs)
