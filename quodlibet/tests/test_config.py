# -*- coding: utf-8 -*-
from tests import TestCase, add

from quodlibet import config


class Tconfig(TestCase):
    def setUp(self):
        config.init()
        config.add_section("foo")

    def test_set(self):
        config.set("foo", "bar", 1)
        self.failUnlessEqual(config.get("foo", "bar"), "1")
        self.failUnlessEqual(config.getint("foo", "bar"), 1)

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
