# -*- coding: utf-8 -*-
from tests import TestCase

from quodlibet.qltk.playorder import PlayOrder
import quodlibet.config
import quodlibet.plugins


class TPlayOrder(TestCase):

    def setUp(self):
        quodlibet.plugins.init()
        quodlibet.config.init()

        self.order = None
        self.volume = 0
        self.replaygain_profiles = [None, None, None]
        self.po = PlayOrder(self, self)

    def tearDown(self):
        self.po.destroy()
        quodlibet.plugins.quit()
        quodlibet.config.quit()

    def test_initial(self):
        self.failUnlessEqual(self.po.get_active_name(), "inorder")
        self.failUnless(self.replaygain_profiles[2], ["album", "track"])

    def test_unknown_name(self):
        self.assertRaises(ValueError, self.po.set_active_by_name, "foobar")

    def test_unknown_index(self):
        self.assertRaises(IndexError, self.po.set_active_by_index, 999)

    def test_set_name(self):
        self.po.set_active_by_name("weighted")
        self.failUnlessEqual(self.po.get_active_name(), "weighted")

    def test_replay_gain(self):
        self.po.set_active_by_name("weighted")
        self.failUnlessEqual(self.replaygain_profiles[2], ["track"])
        self.po.set_active_by_name("inorder")
        self.failUnlessEqual(self.replaygain_profiles[2], ["album", "track"])

    def test_set_int(self):
        old = self.po.get_active_name()
        self.po.set_active_by_index(3)
        self.failIfEqual(self.po.get_active_name(), old)

    def test_get_name(self):
        orders = ["inorder", "shuffle", "weighted", "onesong"]
        for i, name in enumerate(orders):
            self.po.set_active_by_name(name)
            self.failUnlessEqual(self.po.get_active_name(), name)

    def test_shuffle(self):
        self.assertEqual(self.po.get_active_name(), "inorder")
        self.po.set_shuffle(True)
        self.assertTrue(self.po.get_shuffle())
        self.assertEqual(self.po.get_active_name(), "shuffle")

    def test_shuffle_weighted(self):
        self.po.set_active_by_name("weighted")
        self.assertTrue(self.po.get_shuffle())
        self.po.set_shuffle(False)
        self.assertEqual(self.po.get_active_name(), "inorder")
        self.po.set_shuffle(True)
        self.assertTrue(self.po.get_shuffle())
        self.assertEqual(self.po.get_active_name(), "weighted")
