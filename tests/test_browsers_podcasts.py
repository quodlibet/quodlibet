# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
from _pytest.fixtures import fixture
from gi.repository import Gtk

import quodlibet.config
from quodlibet.browsers.podcasts import Podcasts, AddFeedDialog, Feed
from quodlibet.library import SongLibrary
from quodlibet.util.config import Config
from senf import fsn2uri
from tests import TestCase, get_data_path

TEST_URL = u"https://a@b:foo.example.com?bar=baz&quxx#anchor"


class TAudioFeeds(TestCase):
    def setUp(self):
        quodlibet.config.init()
        self.library = SongLibrary()
        self.bar = Podcasts(self.library)

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
        fn = get_data_path('valid_podcast.xml')
        feed = Feed(fsn2uri(fn))
        result = feed.parse()
        # Assume en_US / en_GB locale here in tests
        self.failIfEqual(feed.name, "Unknown", msg="Didn't find feed name")
        # Do this after the above, as many exceptions can be swallowed
        self.failUnless(result)
        self.failUnlessEqual(len(feed), 2)
        self.failUnlessEqual(feed[0]('title'),
                             'Full Episode: Tuesday, November 28, 2017')

    def tearDown(self):
        quodlibet.config.quit()


@fixture
def config():
    quodlibet.config.init()
    yield quodlibet.config
    quodlibet.config.quit()


@fixture
def podcasts():
    library = SongLibrary()
    return Podcasts(library)


def test_menu_items_can_be_clicked(config: Config, podcasts: Podcasts):
    view = podcasts._view
    view.popup_menu = lambda *args: True
    menu = podcasts._popup_menu(None)
    assert menu
    for item in menu.get_children():
        item.emit('activate')
