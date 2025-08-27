# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import time

from tests import TestCase

from gi.repository import Gtk

from quodlibet import config
from quodlibet import const
from quodlibet.browsers.soundcloud import SoundcloudBrowser
from quodlibet.browsers.soundcloud.api import SoundcloudApiClient
from quodlibet.browsers.soundcloud.query import SoundcloudQuery, convert_time
from quodlibet.query import QueryType
from quodlibet.util.dprint import print_d
from tests.test_browsers__base import TBrowserBase

NONE = set()


class TestExtract(TestCase):
    @classmethod
    def setUpClass(cls):
        const.DEBUG = True

    @classmethod
    def tearDownClass(cls):
        const.DEBUG = False

    def test_extract_single_tag(self):
        self.verify("artist=jay z", {"jay z"})

    def test_extract_unsupported(self):
        self.assertEqual(
            SoundcloudQuery("musicbrainz_discid=12345").type, QueryType.INVALID
        )

    def test_extract_composite_text(self):
        self.verify("&(foo, bar)", {"foo", "bar"})
        self.verify("|(either, or)", {"either", "or"})

    def test_numeric_simple(self):
        self.verify("#(length=180)", {"180000"}, term="duration")

    def test_extract_date(self):
        now = int(time.time())
        terms = SoundcloudQuery("#(date>today)", clock=lambda: now).terms
        self.assertEqual(terms["created_at[from]"].pop(), convert_time(now - 86400))

    def test_numeric_relative(self):
        self.verify("#(length>180)", {"180000"}, term="duration[from]")
        self.verify("#(180<=length)", {"180000"}, term="duration[from]")
        self.verify("#(length<360)", {"360000"}, term="duration[to]")
        self.verify("#(360>=length)", {"360000"}, term="duration[to]")

    def test_extract_tag_inter(self):
        self.verify("genre=&(jazz, funk)", {"jazz", "funk"})

    def test_extract_tag_union(self):
        self.verify("genre=|(jazz, funk)", {"jazz", "funk"})

    def test_extract_complex(self):
        self.verify("&(artist='foo', genre=|(rock, metal))", {"foo", "rock", "metal"})

    def verify(self, text, expected, term="q"):
        print_d(f"Trying '{text}'...")
        terms = SoundcloudQuery(text).terms
        msg = f"terms[{term}] wasn't {expected!r}. Full terms: {terms!r}"
        assert terms[term] == expected, msg


class TestMenu(TBrowserBase):
    Kind = SoundcloudBrowser

    def test_songsmenu_has_information_but_no_edit(self):
        menu = self.b.menu([], self.library, [])
        assert menu
        items = [
            item.get_label()
            for item in menu.get_children()
            if type(item) is not Gtk.SeparatorMenuItem
        ]
        # We're always in en_US
        assert "_Rating" in items
        assert "_Information" in items, "Should have included Information"
        assert "_Edit…" not in items, "Shouldn't have included edit"


class TestHttpsDefault(TestCase):
    def setUp(self):
        config.init()

    def tearDown(self):
        config.quit()

    def test_setup_default(self):
        msg = "API client should use HTTPS"
        assert SoundcloudApiClient().root.startswith("https://"), msg
