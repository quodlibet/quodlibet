# -*- coding: utf-8 -*-
from tests import TestCase

import cairo
from gi.repository import Gtk, GdkPixbuf

from quodlibet.qltk.image import set_renderer_from_pbosf, \
    set_image_from_pbosf, get_scale_factor, pbosf_get_property_name, \
    get_pbosf_for_pixbuf


class TImageUtils(TestCase):

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
