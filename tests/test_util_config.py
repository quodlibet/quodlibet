# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
from tests import TestCase, mkstemp
from .helper import temp_filename

from quodlibet.util.config import Config, Error, ConfigProxy


class TConfig(TestCase):

    def test_set_default_only(self):
        conf = Config()
        self.assertRaises(Error, conf.set, "foo", "bar", 1)
        conf.defaults.add_section("foo")
        conf.set("foo", "bar", 1)

    def test_options(self):
        conf = Config()
        self.assertRaises(Error, conf.options, "foo")
        conf.defaults.add_section("foo")
        self.assertEqual(conf.options("foo"), [])
        conf.defaults.set("foo", "bar", 1)
        conf.defaults.set("foo", "blah", 1)
        conf.set("foo", "blah", 1)
        conf.set("foo", "quux", 1)
        self.assertEqual(conf.options("foo"), ["blah", "quux", "bar"])
        conf.defaults.clear()

    def test_options_no_default(self):
        conf = Config()
        conf.add_section("foo")
        self.assertEqual(conf.options("foo"), [])

    def test_has_section(self):
        conf = Config()
        self.assertFalse(conf.has_section("foo"))
        conf.defaults.add_section("foo")
        self.assertTrue(conf.has_section("foo"))
        conf.add_section("foo")
        conf.defaults.clear()
        self.assertTrue(conf.has_section("foo"))
        conf.clear()
        self.assertFalse(conf.has_section("foo"))

    def test_read_garbage_file(self):
        conf = Config()
        garbage = b"\xf1=\xab\xac"

        fd, filename = mkstemp()
        os.close(fd)
        with open(filename, "wb") as f:
            f.write(garbage)

        self.assertRaises(Error, conf.read, filename)
        os.remove(filename)

    def test_set(self):
        conf = Config()
        conf.add_section("foo")
        conf.set("foo", "bar", 1)
        self.assertEqual(conf.get("foo", "bar"), "1")
        self.assertEqual(conf.getint("foo", "bar"), 1)

    def test_setbytes(self):
        conf = Config()
        conf.add_section("foo")
        conf.setbytes("foo", "bar", b"\xff\xff")
        assert conf.getbytes("foo", "bar") == b"\xff\xff"

    def test_getbytes(self):
        conf = Config()
        assert conf.getbytes("foo", "bar", b"\xff") == b"\xff"

    def test_reset(self):
        conf = Config()
        conf.defaults.add_section("player")
        conf.defaults.set("player", "backend", "blah")
        conf.set("player", "backend", "foo")
        self.assertEqual(conf.get("player", "backend"), "foo")
        conf.reset("player", "backend")
        conf.defaults.set("player", "backend", "blah_new")
        self.assertEqual(conf.get("player", "backend"), "blah_new")

    def test_reset_no_section(self):
        conf = Config()
        conf.defaults.add_section("player")
        conf.defaults.set("player", "backend", "blah")
        conf.reset("player", "backend")
        assert conf.get("player", "backend") == "blah"

    def test_initial_after_set(self):
        conf = Config()
        conf.add_section("player")
        conf.set("player", "backend", "orig")
        conf.defaults.add_section("player")
        conf.defaults.set("player", "backend", "initial")
        self.assertEqual(conf.get("player", "backend"), "orig")
        self.assertEqual(conf.defaults.get("player", "backend"), "initial")
        conf.reset("player", "backend")
        self.assertEqual(conf.get("player", "backend"), "initial")

    def test_get_fallback_default(self):
        conf = Config()

        conf.defaults.add_section("get")
        self.assertRaises(Error, conf.get, "get", "bar")
        conf.defaults.set("get", "bar", 1)
        self.assertEqual(conf.get("get", "bar"), "1")

        conf.defaults.add_section("getboolean")
        self.assertRaises(Error, conf.getboolean, "getboolean", "bar")
        conf.defaults.set("getboolean", "bar", True)
        self.assertEqual(conf.getboolean("getboolean", "bar"), True)

        conf.defaults.add_section("getfloat")
        self.assertRaises(Error, conf.getfloat, "getfloat", "bar")
        conf.defaults.set("getfloat", "bar", 1.0)
        self.assertEqual(conf.getfloat("getfloat", "bar"), 1.0)

        conf.defaults.add_section("getint")
        self.assertRaises(Error, conf.getint, "getint", "bar")
        conf.defaults.set("getint", "bar", 42)
        self.assertEqual(conf.getint("getint", "bar"), 42)

        conf.defaults.add_section("getlist")
        self.assertRaises(Error, conf.getlist, "getlist", "bar")
        conf.defaults.setlist("getlist", "bar", [1, 2, 3])
        self.assertEqual(conf.getlist("getlist", "bar"), ["1", "2", "3"])

    def test_get(self):
        conf = Config()
        conf.add_section("foo")

        conf.set("foo", "int", "1")
        conf.set("foo", "float", "1.25")
        conf.set("foo", "str", "foobar")
        conf.set("foo", "bool", "True")
        self.assertEqual(conf.getint("foo", "int"), 1)
        self.assertEqual(conf.getfloat("foo", "float"), 1.25)
        self.assertEqual(conf.get("foo", "str"), "foobar")
        self.assertEqual(conf.getboolean("foo", "bool"), True)

    def test_get_invalid_data(self):
        conf = Config()
        conf.add_section("foo")
        conf.set("foo", "bla", "xx;,,;\n\n\naa")
        self.assertTrue(conf.getboolean("foo", "bla", True))
        self.assertEqual(conf.getint("foo", "bla", 42), 42)
        self.assertEqual(conf.getfloat("foo", "bla", 1.5), 1.5)
        self.assertEqual(conf.getstringlist("foo", "bla", ["baz"]), ["baz"])

    def test_getint_float(self):
        conf = Config()
        conf.add_section("foo")
        conf.set("foo", "float", "1.25")
        self.assertEqual(conf.getint("foo", "float"), 1)

    def test_get_default(self):
        conf = Config()
        conf.add_section("foo")

        self.assertEqual(conf.getboolean("foo", "nothing", True), True)
        self.assertEqual(conf.getint("foo", "nothing", 42), 42)
        self.assertEqual(conf.getfloat("foo", "nothing", 42.42), 42.42)
        self.assertEqual(conf.get("foo", "nothing", "foo"), "foo")

    def test_stringlist_simple(self):
        conf = Config()
        conf.add_section("foo")

        self.assertFalse(conf.get("foo", "bar", None))
        vals = ["one", "two", "three"]
        conf.setstringlist("foo", "bar", vals)
        self.assertEqual(conf.getstringlist("foo", "bar"), vals)

    def test_stringlist_mixed(self):
        conf = Config()
        conf.add_section("foo")

        self.assertFalse(conf.get("foo", "bar", None))
        conf.setstringlist("foo", "bar", ["one", 2])
        self.assertEqual(conf.getstringlist("foo", "bar"), ["one", "2"])

    def test_stringlist_quoting(self):
        conf = Config()
        conf.add_section("foo")

        self.assertFalse(conf.get("foo", "bar", None))
        vals = ["foo's gold", "bar, \"best\" 'ever'",
                "le goût d'œufs à Noël"]
        conf.setstringlist("foo", "bar", vals)
        self.assertEqual(conf.getstringlist("foo", "bar"), vals)

    def test_stringlist_spaces(self):
        conf = Config()
        conf.add_section("foo")

        vals = [" ", "  ", " \t ", " \n \n"]
        conf.setstringlist("foo", "bar", vals)
        self.assertEqual(conf.getstringlist("foo", "bar"), vals)

    def test_stringlist_invalid_encoding(self):
        conf = Config()
        conf.add_section("foo")
        conf.setbytes("foo", "bar", b"\xff\xff\xff\xff\xff\xff")

    def test_getlist(self):
        conf = Config()
        conf.add_section("foo")
        self.assertEqual(conf.getlist("foo", "bar", ["arg"]), ["arg"])
        conf.set("foo", "bar", "abc,fo:o\\,bar")
        self.assertEqual(conf.getlist("foo", "bar"), ["abc", "fo:o,bar"])
        self.assertEqual(conf.getlist("foo", "bar", sep=":"),
                         ["abc,fo", "o\\,bar"])

        conf.set("foo", "bar", "")
        self.assertEqual(conf.getlist("foo", "bar"), [""])

    def test_setlist(self):
        conf = Config()
        conf.add_section("foo")
        conf.setlist("foo", "bar", [" a", ",", "c"])
        self.assertEqual(conf.getlist("foo", "bar"), [" a", ",", "c"])
        self.assertEqual(conf.get("foo", "bar"), " a,\\,,c")
        conf.setlist("foo", "bar", [" a", ",", "c"], sep=":")
        self.assertEqual(conf.get("foo", "bar"), " a:,:c")

    def test_versioning_disabled(self):
        # we don't pass a version, so versioning is disabled
        conf = Config()
        self.assertRaises(Error, conf.get_version)
        with temp_filename() as filename:
            conf.read(filename)
        self.assertRaises(Error, conf.register_upgrade_function, lambda: None)

    def test_versioning_upgrade_func(self):
        called = []

        with temp_filename() as filename:
            conf = Config(version=0)

            def func(*args):
                called.append(args)

            conf.register_upgrade_function(func)
            self.assertRaises(Error, conf.get_version)
            conf.read(filename)
            self.assertEqual(conf.get_version(), -1)
            conf.register_upgrade_function(func)

        self.assertEqual([(conf, -1, 0), (conf, -1, 0)], called)

    def test_versioning(self):
        with temp_filename() as filename:
            conf = Config(version=41)
            conf.add_section("foo")
            conf.set("foo", "bar", "quux")
            conf.write(filename)
            self.assertRaises(Error, conf.get_version)

            # old was 41, we have 42, so upgrade
            def func(config, old, new):
                if old < 42:
                    config.set("foo", "bar", "nope")
            conf = Config(version=42)
            conf.register_upgrade_function(func)
            conf.read(filename)
            self.assertEqual(conf.get_version(), 41)
            self.assertEqual(conf.get("foo", "bar"), "nope")

            # write doesn't change version
            conf.write(filename)
            self.assertEqual(conf.get_version(), 41)

            # but if we load again, it does
            conf.read(filename)
            self.assertEqual(conf.get_version(), 42)

    def test_upgrade_first_read(self):
        # don't run upgrade funcs if there is no config file yet
        with temp_filename() as filename:
            pass

        conf = Config(version=41)

        def func(*args):
            self.assertTrue(False)
        conf.register_upgrade_function(func)
        conf.read(filename)


class TConfigProxy(TestCase):

    def setUp(self):
        conf = Config()
        conf.defaults.add_section("somesection")
        self.proxy = ConfigProxy(conf, "somesection")

    def test_getters_setters(self):
        self.proxy.set("foo", "bar")
        self.assertEqual(self.proxy.get("foo"), "bar")

        self.proxy.set("foo", 1.5)
        self.assertEqual(self.proxy.getfloat("foo"), 1.5)

        self.proxy.set("foo", 15)
        self.assertEqual(self.proxy.getint("foo"), 15)

        self.proxy.set("foo", False)
        self.assertEqual(self.proxy.getboolean("foo"), False)

        self.proxy.setbytes("foo", b"\xff")
        assert self.proxy.getbytes("foo") == b"\xff"

    def test_default(self):
        self.assertEqual(self.proxy.get("foo", "quux"), "quux")

    def test_get_initial(self):
        self.proxy.defaults.set("a", 3.0)
        self.assertEqual(self.proxy.defaults.get("a"), "3.0")

    def test_initial_and_reset(self):
        self.proxy.defaults.set("bla", "baz")
        self.assertEqual(self.proxy.get("bla"), "baz")
        self.proxy.set("bla", "nope")
        self.assertEqual(self.proxy.get("bla"), "nope")
        self.proxy.reset("bla")
        self.assertEqual(self.proxy.get("bla"), "baz")
