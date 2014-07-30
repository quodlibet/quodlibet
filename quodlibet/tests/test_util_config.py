# -*- coding: utf-8 -*-
import os
from tests import TestCase, mkstemp
from helper import temp_filename

from quodlibet.util.config import Config, Error


class TConfig(TestCase):

    def test_read_garbage_file(self):
        conf = Config()
        garbage = "\xf1=\xab\xac"

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
        self.failUnlessEqual(conf.get("foo", "bar"), "1")
        self.failUnlessEqual(conf.getint("foo", "bar"), 1)

    def test_reset(self):
        conf = Config()
        conf.add_section("player")
        conf.set_inital("player", "backend", "blah")
        conf.set("player", "backend", "foo")
        self.assertEqual(conf.get("player", "backend"), "foo")
        conf.reset("player", "backend")
        self.assertEqual(conf.get("player", "backend"), "blah")

    def test_get(self):
        conf = Config()
        conf.add_section("foo")

        conf.set("foo", "int", "1")
        conf.set("foo", "float", "1.25")
        conf.set("foo", "str", "foobar")
        conf.set("foo", "bool", "True")
        self.failUnlessEqual(conf.getint("foo", "int"), 1)
        self.failUnlessEqual(conf.getfloat("foo", "float"), 1.25)
        self.failUnlessEqual(conf.get("foo", "str"), "foobar")
        self.failUnlessEqual(conf.getboolean("foo", "bool"), True)

    def test_get_default(self):
        conf = Config()
        conf.add_section("foo")

        self.failUnlessEqual(conf.getboolean("foo", "nothing", True), True)
        self.failUnlessEqual(conf.getint("foo", "nothing", 42), 42)
        self.failUnlessEqual(conf.getfloat("foo", "nothing", 42.42), 42.42)
        self.failUnlessEqual(conf.get("foo", "nothing", "foo"), "foo")

    def test_get_default_raises(self):
        conf = Config()
        conf.add_section("foo")

        self.assertRaises(ValueError, conf.getboolean, "foo", "nothing", "")
        self.assertRaises(ValueError, conf.getint, "foo", "nothing", "")
        self.assertRaises(ValueError, conf.getfloat, "foo", "nothing", "")

    def test_setdefault_no_defaulting(self):
        conf = Config()
        conf.add_section("foo")

        self.failUnlessEqual(None, conf.get("foo", "bar", None))
        conf.set("foo", "bar", "blah")
        conf.setdefault("foo", "bar", "xxx")
        self.failUnlessEqual("blah", conf.get("foo", "bar"))

    def test_setdefault_defaulting(self):
        conf = Config()
        conf.add_section("foo")

        self.failUnlessEqual(None, conf.get("foo", "bar", None))
        conf.setdefault("foo", "bar", "xxx")
        self.failUnlessEqual("xxx", conf.get("foo", "bar"))

    def test_stringlist_simple(self):
        conf = Config()
        conf.add_section("foo")

        self.failIf(conf.get("foo", "bar", None))
        vals = ["one", "two", "three"]
        conf.setstringlist("foo", "bar", vals)
        self.failUnlessEqual(conf.getstringlist("foo", "bar"), vals)

    def test_stringlist_mixed(self):
        conf = Config()
        conf.add_section("foo")

        self.failIf(conf.get("foo", "bar", None))
        conf.setstringlist("foo", "bar", ["one", 2])
        self.failUnlessEqual(conf.getstringlist("foo", "bar"), ["one", "2"])

    def test_stringlist_quoting(self):
        conf = Config()
        conf.add_section("foo")

        self.failIf(conf.get("foo", "bar", None))
        vals = ["foo's gold", "bar, \"best\" 'ever'",
                u"le goût d'œufs à Noël"]
        conf.setstringlist("foo", "bar", vals)
        self.failUnlessEqual(conf.getstringlist("foo", "bar"), vals)

    def test_stringlist_spaces(self):
        conf = Config()
        conf.add_section("foo")

        vals = [" ", "  ", " \t ", " \n \n"]
        conf.setstringlist("foo", "bar", vals)
        self.failUnlessEqual(conf.getstringlist("foo", "bar"), vals)

    def test_stringlist_invalid_encoding(self):
        conf = Config()
        conf.add_section("foo")
        conf.set("foo", "bar", "\xff\xff\xff\xff\xff\xff")
        self.assertRaises(Error, conf.getstringlist, "foo", "bar")

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
