# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from collections.abc import Generator

import pytest

import quodlibet.config
from quodlibet.browsers.filesystem import FileSystem
from quodlibet.library import SongLibrary


@pytest.fixture
def bar() -> Generator[FileSystem, None, None]:
    quodlibet.config.init()
    bar = FileSystem(SongLibrary())
    yield bar
    bar.destroy()
    quodlibet.config.quit()


class TestFileSystem:
    def test_can_filter(self, bar):
        for key in ["foo", "title", "fake~key", "~woobar", "~#huh"]:
            assert not bar.can_filter(key)
        assert bar.can_filter("~dirname")
