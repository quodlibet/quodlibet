# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk

from quodlibet.qltk.paned import RVPaned, RHPaned, ConfigRVPaned
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
