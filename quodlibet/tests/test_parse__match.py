from tests import TestCase, add

from quodlibet.parse._match import map_numeric_op, ParseError

class TNumericOp(TestCase):
    TIME = 424242

    def test_time_op(self):
        # lastplayed less than 10 seconds ago
        o, v = map_numeric_op("lastplayed", "<", "10", time_=self.TIME)
        self.failUnless(o(self.TIME - 5, v))

        # laststarted more than 1 day ago
        o, v = map_numeric_op("laststarted", ">", "1 day", time_=self.TIME)
        self.failUnless(o(self.TIME - (3600 * 25), v))

        # added less than 4 minutes and 30 seconds ago
        o, v = map_numeric_op("added", "<", "4:30", time_=self.TIME)
        self.failUnless(o(self.TIME - (4 * 60 + 15), v))
        self.failIf(o(self.TIME - (4 * 60 + 35), v))

    def test_time_unit(self):
        t = map_numeric_op("mtime", "=", "now", time_=self.TIME)[1]
        self.failUnlessEqual(t, self.TIME)

        t = map_numeric_op("mtime", ">", "today", time_=self.TIME)[1]
        self.failUnlessEqual(t, self.TIME - (3600 * 24))

        t = map_numeric_op("mtime", ">", "2 days ago", time_=self.TIME)[1]
        self.failUnlessEqual(t, self.TIME - (3600 * 24 * 2))

        t = map_numeric_op("mtime", ">", "3.0 weeks ago", time_=self.TIME)[1]
        self.failUnlessEqual(t, self.TIME - (3600 * 24 * 7 * 3))

        t = map_numeric_op("mtime", ">", "1 year ago", time_=self.TIME)[1]
        self.failUnlessEqual(t, self.TIME - (3600 * 24 * 365))

        t = map_numeric_op("mtime", ">", "5 hours ago", time_=self.TIME)[1]
        self.failUnlessEqual(t, self.TIME - (3600 * 5))

        t = map_numeric_op("mtime", ">", "1 minute", time_=self.TIME)[1]
        self.failUnlessEqual(t, self.TIME - (60))

        self.failUnlessRaises(ParseError,
                              map_numeric_op, "mtime", "<", "3 foo")

        self.failUnlessRaises(ParseError,
                              map_numeric_op, "mtime", "<", "bar")

    def test_time_format(self):
        o, v = map_numeric_op("length", ">", "5:10")
        self.failUnless(o(5 * 60 + 12, v))

        o, v = map_numeric_op("length", "=", "10:5:10")
        self.failUnless(o((3600 * 10) + (5 * 60) + 10, v))

    def test_float(self):
        o, v = map_numeric_op("rating", ">", "0.5")
        self.failUnless(o(0.6, v))
        self.failIf(o(0.5, v))

    def test_size(self):
        o, v = map_numeric_op("filesize", ">", "10MB")
        self.failUnless(o(1024 * 1024 * 11, v))
        self.failIf(o(1024 * 1024 * 9, v))

        map_numeric_op("filesize", ">", "10kB")
        map_numeric_op("filesize", ">", "10bytes")
        map_numeric_op("filesize", ">", "10G")
        map_numeric_op("filesize", ">", "10m")

        self.failUnlessRaises(ParseError,
                              map_numeric_op, "foobar", ">", "10MB")

        self.failUnlessRaises(ParseError,
                              map_numeric_op, "filesize", ">", "10X")

        self.failUnlessRaises(ParseError,
                              map_numeric_op, "filesize", "!", "10MB")

    def test_simple(self):
        o, v = map_numeric_op("playcount", "<=", "5")
        self.failUnless(o(5, v))
        self.failIf(o(5.01, v))

add(TNumericOp)
