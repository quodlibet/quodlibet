# -*- coding: utf-8 -*-
from tests import TestCase

import cairo
from gi.repository import Gtk, GdkPixbuf, Gdk

from quodlibet.qltk.image import set_renderer_from_pbosf, \
    set_image_from_pbosf, get_scale_factor, pbosf_get_property_name, \
    get_pbosf_for_pixbuf, scale, calc_scale_size, add_border, \
    add_border_widget, pbosf_get_width, pbosf_get_height, \
    set_ctx_source_from_pbosf, pbosf_get_rect


class TImageUtils(TestCase):

    def setUp(self):
        self.small = GdkPixbuf.Pixbuf.new(
            GdkPixbuf.Colorspace.RGB, True, 8, 10, 20)
        self.wide = GdkPixbuf.Pixbuf.new(
            GdkPixbuf.Colorspace.RGB, True, 8, 150, 10)
        self.high = GdkPixbuf.Pixbuf.new(
            GdkPixbuf.Colorspace.RGB, True, 8, 10, 100)

    def test_scale_factor(self):
        w = Gtk.Button()
        self.assertTrue(get_scale_factor(w) in range(10))

    def test_get_pbosf_for_pixbuf(self):
        w = Gtk.Button()
        rgb = GdkPixbuf.Colorspace.RGB
        newpb = GdkPixbuf.Pixbuf.new(rgb, True, 8, 10, 10)
        pbosf = get_pbosf_for_pixbuf(w, newpb)
        self.assertTrue(isinstance(pbosf, (GdkPixbuf.Pixbuf, cairo.Surface)))

    def test_pbosf_get_property_name(self):
        sf = cairo.ImageSurface(cairo.FORMAT_RGB24, 10, 10)
        self.assertEqual(pbosf_get_property_name(sf), "surface")

        rgb = GdkPixbuf.Colorspace.RGB
        newpb = GdkPixbuf.Pixbuf.new(rgb, True, 8, 10, 10)
        self.assertEqual(pbosf_get_property_name(newpb), "pixbuf")

        # We pass None to clear an image, fall back to pixbuf in this case
        self.assertEqual(pbosf_get_property_name(None), "pixbuf")

    def test_set_image_from_pbosf(self):
        image = Gtk.Image()

        if hasattr(Gtk.Image, "new_from_surface"):
            sf = cairo.ImageSurface(cairo.FORMAT_RGB24, 10, 10)
            set_image_from_pbosf(image, sf)
            self.assertTrue(image.props.surface)

        rgb = GdkPixbuf.Colorspace.RGB
        newpb = GdkPixbuf.Pixbuf.new(rgb, True, 8, 10, 10)
        set_image_from_pbosf(image, newpb)
        self.assertTrue(image.props.pixbuf)

    def test_set_renderer_from_pbosf(self):
        cell = Gtk.CellRendererPixbuf()

        if hasattr(Gtk.Image, "new_from_surface"):
            sf = cairo.ImageSurface(cairo.FORMAT_RGB24, 10, 10)
            set_renderer_from_pbosf(cell, sf)

        rgb = GdkPixbuf.Colorspace.RGB
        newpb = GdkPixbuf.Pixbuf.new(rgb, True, 8, 10, 10)
        set_renderer_from_pbosf(cell, newpb)

        set_renderer_from_pbosf(cell, None)

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

    def test_pbosf_get_width_height(self):
        w = Gtk.Button()
        rgb = GdkPixbuf.Colorspace.RGB
        s = get_scale_factor(w)
        newpb = GdkPixbuf.Pixbuf.new(rgb, True, 8, 10 * s, 15 * s)
        pbosf = get_pbosf_for_pixbuf(w, newpb)
        self.assertEqual(pbosf_get_width(pbosf), 10)
        self.assertEqual(pbosf_get_height(pbosf), 15)

    def test_set_ctx_source_from_pbosf(self):
        sf = cairo.ImageSurface(cairo.FORMAT_RGB24, 10, 10)
        ctx = cairo.Context(sf)

        surface = cairo.ImageSurface(cairo.FORMAT_RGB24, 10, 10)
        pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 4, 4)
        set_ctx_source_from_pbosf(ctx, surface)
        set_ctx_source_from_pbosf(ctx, pixbuf)

    def test_pbosf_get_rect(self):
        sf = cairo.ImageSurface(cairo.FORMAT_RGB24, 10, 11)
        self.assertEqual(pbosf_get_rect(sf), (0, 0, 10, 11))
        pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 4, 5)
        self.assertEqual(pbosf_get_rect(pixbuf), (0, 0, 4, 5))
