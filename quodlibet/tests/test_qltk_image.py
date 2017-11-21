# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase

import cairo
from gi.repository import Gtk, GdkPixbuf, Gdk

from quodlibet.qltk.image import get_surface_extents, get_surface_for_pixbuf, \
    scale, calc_scale_size, add_border, add_border_widget


class TImageUtils(TestCase):

    def setUp(self):
        self.small = GdkPixbuf.Pixbuf.new(
            GdkPixbuf.Colorspace.RGB, True, 8, 10, 20)
        self.wide = GdkPixbuf.Pixbuf.new(
            GdkPixbuf.Colorspace.RGB, True, 8, 150, 10)
        self.high = GdkPixbuf.Pixbuf.new(
            GdkPixbuf.Colorspace.RGB, True, 8, 10, 100)

    def test_get_surface_for_pixbuf(self):
        w = Gtk.Button()
        rgb = GdkPixbuf.Colorspace.RGB
        newpb = GdkPixbuf.Pixbuf.new(rgb, True, 8, 10, 10)
        surface = get_surface_for_pixbuf(w, newpb)
        self.assertTrue(isinstance(surface, cairo.Surface))

    def test_scale(s):
        nw = scale(s.wide, (50, 30))
        s.failUnlessEqual((nw.get_width(), nw.get_height()), (50, 3))

        nh = scale(s.high, (100, 20))
        s.failUnlessEqual((nh.get_width(), nh.get_height()), (2, 20))

        ns = scale(s.small, (500, 300))
        s.failUnlessEqual((ns.get_width(), ns.get_height()), (150, 300))

        ns = scale(s.small, (500, 300), scale_up=False)
        s.failUnlessEqual((ns.get_width(), ns.get_height()), (10, 20))

    def test_calc_scale_size(self):
        self.assertRaises(ValueError,
                          calc_scale_size, (1, 1), (1, 0))
        res = calc_scale_size((100, 100), (500, 100))
        self.assertEqual(res, (100, 20))

    def test_add_border(self):
        color = Gdk.RGBA()
        w, h = self.small.get_width(), self.small.get_height()
        res = add_border(self.small, color)
        self.assertEqual(res.get_width(), w + 2)
        self.assertEqual(res.get_height(), h + 2)

        res = add_border(self.small, color)
        self.assertEqual(res.get_width(), w + 2)
        self.assertEqual(res.get_height(), h + 2)

        res = add_border(self.small, color, width=2)
        self.assertEqual(res.get_width(), w + 4)
        self.assertEqual(res.get_height(), h + 4)

    def test_add_border_widget(self):
        widget = Gtk.Button()
        add_border_widget(self.small, widget)

    def test_get_surface_extents(self):
        sf = cairo.ImageSurface(cairo.FORMAT_RGB24, 10, 11)
        self.assertEqual(get_surface_extents(sf), (0, 0, 10, 11))
