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

    def test_get_default_wrong(self):
        self.assertRaises(ValueError, config.getboolean, "foo", "nothing", "")
        self.assertRaises(ValueError, config.getint, "foo", "nothing", "")
        self.assertRaises(ValueError, config.getfloat, "foo", "nothing", "")

    def tearDown(self):
        config.quit()

add(Tconfig)
