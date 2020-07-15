# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import pathlib

from tests import TestCase, get_data_path

from gi.repository import Gtk
from quodlibet.browsers.audiofeeds import AudioFeeds, AddFeedDialog, Feed
from quodlibet.library import SongLibrary
import quodlibet.config

TEST_URL = u"https://a@b:foo.example.com?bar=baz&quxx#anchor"


class TAudioFeeds(TestCase):
    def setUp(self):
        quodlibet.config.init()
        self.library = SongLibrary()
        self.bar = AudioFeeds(self.library)

    def test_can_filter(self):
        for key in ["foo", "title", "fake~key", "~woobar", "~#huh"]:
            self.failIf(self.bar.can_filter(key))

    def tearDown(self):
        self.bar.destroy()
        self.library.destroy()
        quodlibet.config.quit()


class TAddFeedDialog(TestCase):
    def setUp(self):
        quodlibet.config.init()

    def test_add_feed_takes_uri(self):
        parent = Gtk.Window()
        ret = AddFeedDialog(parent).run(text=TEST_URL, test=True)
        self.failUnlessEqual(ret.uri, TEST_URL)

    def tearDown(self):
        quodlibet.config.quit()


class TFeed(TestCase):

    def setUp(self):
        quodlibet.config.init()

    def test_feed(self):
        fn = get_data_path('valid_feed.xml')
        feed = Feed(pathlib.Path(fn).as_uri())
        result = feed.parse()
        self.failUnless(result)
        self.failUnlessEqual(len(feed), 2)
        self.failUnlessEqual(feed[0]('title'),
                             'Full Episode: Tuesday, November 28, 2017')

    def tearDown(self):
        quodlibet.config.quit()
