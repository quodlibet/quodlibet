from tests import TestCase
from helper import visible

import cairo
from gi.repository import Gtk, GdkPixbuf

from quodlibet.qltk.image import *
from quodlibet import config


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

    def test_render(self):

        class Custom(Gtk.Image):

            def __init__(self, pbosf):
                super(Custom, self).__init__()
                self.pbosf = pbosf
                self.started = False
                self.drawn = False

            def do_draw(self, cairo_context):
                self.started = True
                style_context = self.get_style_context()
                pbosf_render(style_context, cairo_context, self.pbosf, 0, 0)
                self.drawn = True

            def wait_for_draw(self):
                self.queue_draw()
                while not self.started:
                    if not Gtk.main_iteration_do(False):
                        break

        rgb = GdkPixbuf.Colorspace.RGB
        newpb = GdkPixbuf.Pixbuf.new(rgb, True, 8, 10, 10)
        with visible(Custom(newpb)) as w:
            w.wait_for_draw()
            self.assertTrue(w.drawn)

        if hasattr(Gtk.Image, "new_from_surface"):
            sf = cairo.ImageSurface(cairo.FORMAT_RGB24, 10, 10)
            with visible(Custom(sf)) as w:
                w.wait_for_draw()
                self.assertTrue(w.drawn)
