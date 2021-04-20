# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import quodlibet.config
import quodlibet.plugins
from quodlibet.qltk import Icons
from quodlibet.qltk.playorder import OrderShuffle, OrderWeighted, \
    ToggledPlayOrderMenu, Orders, Order, OrderInOrder
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
        # quodlibet.plugins.quit()
        quodlibet.config.quit()

    def test_initial(self):
        self.failIf(self.po.repeated)
        self.failIf(self.po.shuffled)
        self.failUnless(isinstance(self.po.order, OrderInOrder))
        self.failUnless(self.replaygain_profiles[2], ["album", "track"])

    def test_replay_gain(self):
        self.po.shuffled = True
        self.po.shuffler = OrderWeighted
        self.failUnlessEqual(self.replaygain_profiles[2], ["track"])
        self.po.shuffled = False
        self.failUnlessEqual(self.replaygain_profiles[2], ["album", "track"])

    def test_get_name(self):
        orders = [OrderShuffle, OrderWeighted]
        for order in orders:
            self.po.shuffler = order
            self.failUnlessEqual(self.po.shuffler, order)

    def test_shuffle(self):
        self.failIf(self.po.repeated)
        self.po.shuffled = True
        self.assertTrue(self.po.shuffled)
        self.assertEqual(self.po.shuffler, OrderShuffle)
        self.failUnless(isinstance(self.order, OrderShuffle))

    def test_shuffle_defaults_to_inorder(self):
        self.po.shuffler = OrderWeighted
        self.po.shuffled = False
        self.failUnlessEqual(type(self.po.order), OrderInOrder)
        self.po.shuffled = True
        self.assertEqual(self.po.shuffler, OrderWeighted)
        self.failUnlessEqual(type(self.po.order), OrderWeighted)


class FakeOrder(Order):
    name = "fake"


class TToggledPlayOrderMenu(TestCase):

    def setUp(self):
        self.orders = Orders([OrderShuffle, OrderWeighted, FakeOrder])
        self.tpom = ToggledPlayOrderMenu(Icons.AUDIO_X_GENERIC,
                                         orders=self.orders,
                                         current_order=OrderShuffle,
                                         enabled=True)

    def tearDown(self):
        self.tpom.destroy()

    def test_enabled_initially(self):
        self.failUnless(self.tpom.enabled)

    def test_setting_enabled(self):
        self.tpom.enabled = False
        self.failIf(self.tpom.enabled)
        self.tpom.enabled = True
        self.failUnless(self.tpom.enabled)

    def test_initial(self):
        self.failUnlessEqual(self.tpom.current, OrderShuffle)

    def test_unknown_name(self):
        self.assertRaises(ValueError, self.tpom.set_active_by_name, "foobar")

    def test_set_by_name(self):
        self.tpom.set_active_by_name("fake")
        self.failUnlessEqual(self.tpom.current.name, "fake")

    def test_get_name(self):
        for order in self.orders:
            self.tpom.current = order
            self.failUnlessEqual(self.tpom.current, order)

    def test_set_orders(self):
        self.tpom.set_orders([])
        self.failIf(self.tpom.current)
