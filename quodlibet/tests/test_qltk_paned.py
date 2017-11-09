# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from quodlibet.qltk.paned import RVPaned, RHPaned, ConfigRVPaned, \
        MultiRVPaned, MultiRHPaned, ConfigMultiRVPaned, ConfigMultiRHPaned
from quodlibet import config

from . import TestCase
from .helper import visible


class TRPaned(object):
    Kind = None

    def test_ctr(self):
        self.Kind().destroy()

    def test_pre_alloc(self):
        p = self.Kind()
        p.set_relative(0.25)
        self.failUnlessEqual(p.get_relative(), 0.25)
        self.assertRaises(ValueError, p.set_relative, 2.0)
        self.assertRaises(ValueError, p.set_relative, -2.0)

    def test_visible_no_setup(self):
        p = self.Kind()
        with visible(p):
            pass

    def test_visible_pre_setup_children(self):
        p = self.Kind()
        p.pack1(Gtk.Button())
        p.pack2(Gtk.Button())
        p.set_relative(0.75)
        self.failUnlessAlmostEqual(p.get_relative(), 0.75)
        with visible(p, width=200, height=200) as p:
            self.failUnlessAlmostEqual(p.get_relative(), 0.75, 2)

    def test_visible_pre_setup_empty(self):
        p = self.Kind()
        p.set_relative(0.75)
        self.failUnlessEqual(p.get_relative(), 0.75)
        with visible(p) as p:
            self.failUnlessAlmostEqual(p.get_relative(), 0.75, 2)

    def test_min_size_child(self):
        p = self.Kind()
        p.set_size_request(200, 200)
        p.pack1(Gtk.Label(), True, False)
        b2 = Gtk.Button()
        b2.set_size_request(50, 50)
        p.pack2(b2, True, False)
        p.set_relative(0.5)
        with visible(p) as p:
            self.assertEqual(p.get_position(), 100)


class RHPaned(TestCase, TRPaned):
    Kind = RHPaned


class RVPaned(TestCase, TRPaned):
    Kind = RVPaned


class TConfigRPaned(TestCase):

    def setUp(self):
        config.init()

    def tearDown(self):
        config.quit()

    def test_basic(self):
        self.failUnless(config.get("memory", "foobar", None) is None)

        p = ConfigRVPaned("memory", "foobar", 0.75)
        p.pack1(Gtk.Button())
        p.pack2(Gtk.Button())

        with visible(p, width=200, height=200) as p:
            self.failUnlessAlmostEqual(p.get_relative(), 0.75, 2)
            p.props.position = 20
            self.failUnlessAlmostEqual(p.get_relative(), 0.10, 2)

        config_value = config.getfloat("memory", "foobar")
        self.failUnlessAlmostEqual(config_value, 0.10, 2)


class TMultiRPaned(object):
    Kind = None

    def test_set_widgets(self):
        """Test if widgets are properly set and in the correct order."""
        p = self.Kind()

        # 0 widgets
        p.set_widgets([])
        paned = p.get_paned()
        self.assertIsNotNone(paned)
        self.assertIsNone(paned.get_child1())
        self.assertIsNone(paned.get_child2())

        # 1 widget
        sw = Gtk.ScrolledWindow()
        p.set_widgets([sw])
        paned = p.get_paned()
        children = [paned.get_child1(), paned.get_child2()]
        self.assertIn(sw, children)

        # 2 widgets
        sws = [Gtk.ScrolledWindow() for _ in range(2)]
        p.set_widgets(sws)
        paned = p.get_paned()
        self.assertIs(sws[0], paned.get_child1())
        self.assertIs(sws[1], paned.get_child2())

        # 3 wigets
        sws = [Gtk.ScrolledWindow() for _ in range(3)]
        p.set_widgets(sws)

        root_paned = p.get_paned()
        self.assertIs(sws[0], root_paned.get_child1())

        sub_paned = root_paned.get_child2()
        self.assertIs(sws[1], sub_paned.get_child1())
        self.assertIs(sws[2], sub_paned.get_child2())

    def test_make_pane_widths_equal(self):
        p = self.Kind()
        sws = [Gtk.ScrolledWindow() for _ in range(4)]
        p.set_widgets(sws)
        p.make_pane_widths_equal()

        paneds = p._get_paneds()
        self.failUnlessAlmostEqual(paneds[0].get_relative(), 1.0 / 4.0)
        self.failUnlessAlmostEqual(paneds[1].get_relative(), 1.0 / 3.0)
        self.failUnlessAlmostEqual(paneds[2].get_relative(), 1.0 / 2.0)

    def test_change_orientation(self):
        p = self.Kind()
        p.set_widgets([Gtk.ScrolledWindow()])

        opposite = Gtk.Orientation.HORIZONTAL
        horizontal_opposite = True
        if p.get_paned().props.orientation is Gtk.Orientation.HORIZONTAL:
            opposite = Gtk.Orientation.VERTICAL
            horizontal_opposite = False

        p.change_orientation(horizontal=horizontal_opposite)
        for paned in p._get_paneds():
            self.assertIs(paned.props.orientation, opposite)

    def test_destroy(self):
        self.Kind().destroy()


class TMultiRHPaned(TestCase, TMultiRPaned):
    Kind = MultiRHPaned


class TMultiRVPaned(TestCase, TMultiRPaned):
    Kind = MultiRVPaned


class TConfigMultiRPaned(object):

    def setUp(self):
        config.init()

    def tearDown(self):
        config.quit()

    def test_basic(self):
        self.assertTrue(config.get("memory", "pane_widths", None) is None)

        p = self.Kind("memory", "pane_widths")
        sws = [Gtk.ScrolledWindow() for _ in range(3)]
        p.set_widgets(sws)

        paneds = p._get_paneds()
        paneds[0].set_relative(0.4)
        paneds[1].set_relative(0.6)
        p.save_widths()

        widths = config.getstringlist("memory", "pane_widths")
        self.assertAlmostEqual(float(widths[0]), 0.4)
        self.assertAlmostEqual(float(widths[1]), 0.6)

        config.remove_option("memory", "pane_widths")


class TConfigMultiRHPaned(TestCase, TConfigMultiRPaned):
    Kind = ConfigMultiRHPaned


class TConfigMultiRVPaned(TestCase, TConfigMultiRPaned):
    Kind = ConfigMultiRVPaned
