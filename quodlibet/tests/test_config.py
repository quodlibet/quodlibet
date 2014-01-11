# -*- coding: utf-8 -*-
import os
from quodlibet.config import RatingsPrefs
from tests import TestCase, add, mkstemp
from helper import capture_output

from quodlibet import config


class Tconfig(TestCase):
    def setUp(self):
        config.init()
        config.add_section("foo")

    def test_read_garbage_file(self):
        config.quit()

        garbage = "\xf1=\xab\xac"

        fd, filename = mkstemp()
        os.close(fd)
        with open(filename, "wb") as f:
            f.write(garbage)

        with capture_output() as (stdout, stderr):
            config.init(filename)
        self.assertTrue(stderr.getvalue())
        self.assertTrue(config.options("player"))

        invalid_filename = filename + ".not-valid"
        self.assertTrue(os.path.exists(invalid_filename))
        with open(invalid_filename, "rb") as f:
            self.assertEqual(f.read(), garbage)

        os.remove(filename)
        os.remove(invalid_filename)

    def test_set(self):
        config.set("foo", "bar", 1)
        self.failUnlessEqual(config.get("foo", "bar"), "1")
        self.failUnlessEqual(config.getint("foo", "bar"), 1)

    def test_reset(self):
        orig = config.get("player", "backend")
        config.set("player", "backend", "foo")
        self.assertEqual(config.get("player", "backend"), "foo")
        config.reset("player", "backend")
        self.assertEqual(config.get("player", "backend"), orig)

    def test_get(self):
        config.set("foo", "int", "1")
        config.set("foo", "float", "1.25")
        config.set("foo", "str", "foobar")
        config.set("foo", "bool", "True")
        self.failUnlessEqual(config.getint("foo", "int"), 1)
        self.failUnlessEqual(config.getfloat("foo", "float"), 1.25)
        self.failUnlessEqual(config.get("foo", "str"), "foobar")
        self.failUnlessEqual(config.getboolean("foo", "bool"), True)

    def test_get_default(self):
        self.failUnlessEqual(config.getboolean("foo", "nothing", True), True)
        self.failUnlessEqual(config.getint("foo", "nothing", 42), 42)
        self.failUnlessEqual(config.getfloat("foo", "nothing", 42.42), 42.42)
        self.failUnlessEqual(config.get("foo", "nothing", "foo"), "foo")

    def test_get_default_raises(self):
        self.assertRaises(ValueError, config.getboolean, "foo", "nothing", "")
        self.assertRaises(ValueError, config.getint, "foo", "nothing", "")
        self.assertRaises(ValueError, config.getfloat, "foo", "nothing", "")

    def test_setdefault_no_defaulting(self):
        self.failUnlessEqual(None, config.get("foo", "bar", None))
        config.set("foo", "bar", "blah")
        config.setdefault("foo", "bar", "xxx")
        self.failUnlessEqual("blah", config.get("foo", "bar"))

    def test_setdefault_defaulting(self):
        self.failUnlessEqual(None, config.get("foo", "bar", None))
        config.setdefault("foo", "bar", "xxx")
        self.failUnlessEqual("xxx", config.get("foo", "bar"))

    def test_stringlist_simple(self):
        self.failIf(config.get("foo", "bar", None))
        vals = ["one", "two", "three"]
        config.setstringlist("foo", "bar", vals)
        self.failUnlessEqual(config.getstringlist("foo", "bar"), vals)

    def test_stringlist_mixed(self):
        self.failIf(config.get("foo", "bar", None))
        config.setstringlist("foo", "bar", ["one", 2])
        self.failUnlessEqual(config.getstringlist("foo", "bar"), ["one", "2"])

    def test_stringlist_quoting(self):
        self.failIf(config.get("foo", "bar", None))
        vals = ["foo's gold", "bar, \"best\" 'ever'",
                u"le goût d'œufs à Noël"]
        config.setstringlist("foo", "bar", vals)
        self.failUnlessEqual(config.getstringlist("foo", "bar"), vals)

    def test_stringlist_spaces(self):
        vals = [" ", "  ", " \t ", " \n \n"]
        config.setstringlist("foo", "bar", vals)
        self.failUnlessEqual(config.getstringlist("foo", "bar"), vals)

    def test_get_columns_migrates(self):
        self.failIf(config.get("settings", "headers", None))
        self.failIf(config.get("settings", "columns", None))

        headers = "~album ~#replaygain_track_gain foobar"
        config.set("settings", "headers", headers)
        columns = config.get_columns(headers)
        self.failUnlessEqual(columns, ["~album", "~#replaygain_track_gain",
                                       "foobar"])
        self.failIf(config.get("settings", "headers", None))

    def test_get_set_columns(self):
        self.failIf(config.get("settings", "headers", None))
        self.failIf(config.get("settings", "columns", None))
        columns = ["first", "won't", "two words", "4"]
        config.set_columns(columns)
        # First assume caching
        self.failUnlessEqual(columns, config.get_columns())
        # Then without
        self.failUnlessEqual(columns, config.get_columns(refresh=True))
        columns += ["~~another~one"]
        # Test dirtying the cache
        config.set_columns(columns)
        self.failUnlessEqual(columns, config.get_columns())
        self.failUnlessEqual(columns, config.get_columns(refresh=True))
        self.failIf(config.get("settings", "headers", None))

    def tearDown(self):
        config.quit()

add(Tconfig)


class TRatingsPrefs(TestCase):
    initial_number = int(config.INITIAL["settings"]["ratings"])

    def setUp(self):
        config.init()
        self.prefs = RatingsPrefs()

    def test_getters(self):
        # A little pointless, and brittle, but still.
        self.failUnlessEqual(self.prefs.number, self.initial_number)
        self.failUnlessEqual(self.prefs.precision, 1.0 / self.initial_number)
        self.failUnlessEqual(self.prefs.full_symbol, config.INITIAL[
            "settings"]["rating_symbol_full"].decode("utf-8"))
        self.failUnlessEqual(self.prefs.blank_symbol, config.INITIAL[
            "settings"]["rating_symbol_blank"].decode("utf-8"))

    def test_caching(self):
        self.failUnlessEqual(self.prefs.number, self.initial_number)
        self.prefs.number = 10
        self.prefs.default = 0.1
        # Read it back, and it's fine
        self.failUnlessEqual(self.prefs.number, 10)
        self.failUnlessEqual(self.prefs.default, 0.1)
        # .. but modify behind the scenes (unsupported)...
        config.reset("settings", "ratings")
        config.reset("settings", "default_rating")
        # ...and caching will return the old one
        self.failUnlessEqual(self.prefs.number, 10)
        self.failUnlessEqual(self.prefs.default, 0.1)

    def test_all(self):
        self.prefs.number = 5
        # Remember zero is a possible rating too
        self.failUnlessEqual(len(self.prefs.all), 6)
        self.failUnlessEqual(self.prefs.all, [0, 0.2, 0.4, 0.6, 0.8, 1.0])

    def tearDown(self):
        config.quit()

add(TRatingsPrefs)
