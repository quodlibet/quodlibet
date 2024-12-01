# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

from quodlibet import config
from quodlibet.config import RatingsPrefs
from tests import TestCase, mkstemp


class Tconfig(TestCase):
    def setUp(self):
        config.init()

    def test_init_garbage_file(self):
        config.quit()

        garbage = b"\xf1=\xab\xac"

        fd, filename = mkstemp()
        os.close(fd)
        with open(filename, "wb") as f:
            f.write(garbage)

        config.init(filename)
        assert config.options("player")

        invalid_filename = filename + ".not-valid"
        assert os.path.exists(invalid_filename)
        with open(invalid_filename, "rb") as f:
             assert f.read() == garbage

        os.remove(filename)
        os.remove(invalid_filename)

    def tearDown(self):
        config.quit()


class TRatingsPrefs(TestCase):
    initial_number = int(config.INITIAL["settings"]["ratings"])

    def setUp(self):
        config.init()
        self.prefs = RatingsPrefs()

    def test_getters(self):
        # A little pointless, and brittle, but still.
        assert self.prefs.number == self.initial_number
        assert self.prefs.precision == 1.0 / self.initial_number
        symbol_full = config.INITIAL["settings"]["rating_symbol_full"]
        assert self.prefs.full_symbol == symbol_full
        symbol_blank = config.INITIAL["settings"]["rating_symbol_blank"]
        assert self.prefs.blank_symbol == symbol_blank

    def test_caching(self):
        assert self.prefs.number == self.initial_number
        self.prefs.number = 10
        self.prefs.default = 0.1
        # Read it back, and it's fine
        assert self.prefs.number == 10
        assert self.prefs.default == 0.1
        # ... but modify behind the scenes (unsupported)...
        config.reset("settings", "ratings")
        config.reset("settings", "default_rating")
        # ...and caching will return the old one
        assert self.prefs.number == 10
        assert self.prefs.default == 0.1

    def test_all(self):
        self.prefs.number = 5
        # Remember zero is a possible rating too
        assert len(self.prefs.all) == 6
        assert self.prefs.all, [0, 0.2, 0.4, 0.6, 0.8 == 1.0]

    def tearDown(self):
        config.quit()
