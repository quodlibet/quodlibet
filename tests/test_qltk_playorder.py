# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import quodlibet.config
import quodlibet.plugins
from quodlibet.qltk import Icons
from quodlibet.qltk.playorder import (
    OrderShuffle,
    OrderWeighted,
    ToggledPlayOrderMenu,
    Orders,
    Order,
    OrderInOrder,
)
from quodlibet.qltk.playorder import PlayOrderWidget
from tests import TestCase


class TPlayOrderWidget(TestCase):
    def setUp(self):
        quodlibet.config.init()

        self.order = None
        self.volume = 0
        self.replaygain_profiles = [None, None, None]
        self.reset_replaygain = lambda: None
        self.po = PlayOrderWidget(self, self)

    def tearDown(self):
        self.po.destroy()
        quodlibet.config.quit()

    def test_initial(self):
        assert not self.po.repeated
        assert not self.po.shuffled
        assert isinstance(self.po.order, OrderInOrder)
        assert self.replaygain_profiles[2], ["album", "track"]

    def test_replay_gain(self):
        self.po.shuffled = True
        self.po.shuffler = OrderWeighted
        self.assertEqual(self.replaygain_profiles[2], ["track"])
        self.po.shuffled = False
        self.assertEqual(self.replaygain_profiles[2], ["album", "track"])

    def test_get_name(self):
        orders = [OrderShuffle, OrderWeighted]
        for order in orders:
            self.po.shuffler = order
            self.assertEqual(self.po.shuffler, order)

    def test_shuffle(self):
        assert not self.po.repeated
        self.po.shuffled = True
        assert self.po.shuffled
        self.assertEqual(self.po.shuffler, OrderShuffle)
        assert isinstance(self.order, OrderShuffle)

    def test_shuffle_defaults_to_inorder(self):
        self.po.shuffler = OrderWeighted
        self.po.shuffled = False
        self.assertEqual(type(self.po.order), OrderInOrder)
        self.po.shuffled = True
        self.assertEqual(self.po.shuffler, OrderWeighted)
        self.assertEqual(type(self.po.order), OrderWeighted)


class FakeOrder(Order):
    name = "fake"


class TToggledPlayOrderMenu(TestCase):
    def setUp(self):
        self.orders = Orders([OrderShuffle, OrderWeighted, FakeOrder])
        self.tpom = ToggledPlayOrderMenu(
            Icons.AUDIO_X_GENERIC,
            orders=self.orders,
            current_order=OrderShuffle,
            enabled=True,
        )

    def tearDown(self):
        self.tpom.destroy()

    def test_enabled_initially(self):
        assert self.tpom.enabled

    def test_setting_enabled(self):
        self.tpom.enabled = False
        assert not self.tpom.enabled
        self.tpom.enabled = True
        assert self.tpom.enabled

    def test_initial(self):
        self.assertEqual(self.tpom.current, OrderShuffle)

    def test_unknown_name(self):
        self.assertRaises(ValueError, self.tpom.set_active_by_name, "foobar")

    def test_set_by_name(self):
        self.tpom.set_active_by_name("fake")
        self.assertEqual(self.tpom.current.name, "fake")

    def test_get_name(self):
        for order in self.orders:
            self.tpom.current = order
            self.assertEqual(self.tpom.current, order)

    def test_set_orders(self):
        self.tpom.set_orders([])
        assert not self.tpom.current

    def test_playorder_disables_when_order_disappears(self):
        self.tpom.orders = Orders([OrderWeighted, FakeOrder])
        assert not self.tpom.enabled
