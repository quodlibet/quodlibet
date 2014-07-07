from tests import TestCase
from helper import visible

import cairo
from gi.repository import Gtk, GdkPixbuf, GLib

from quodlibet.qltk.image import *
from quodlibet import config


def _has_gi_attr(obj, name):
    # work around using 3.10 gir with 3.8 gtk on windows...
    try:
        getattr(obj, name)
    except (AttributeError, GLib.GError):
        return False
    return True


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

        if _has_gi_attr(Gtk.Image, "new_from_surface"):
            sf = cairo.ImageSurface(cairo.FORMAT_RGB24, 10, 10)
            set_image_from_pbosf(image, sf)
            self.assertTrue(image.props.surface)

        rgb = GdkPixbuf.Colorspace.RGB
        newpb = GdkPixbuf.Pixbuf.new(rgb, True, 8, 10, 10)
        set_image_from_pbosf(image, newpb)
        self.assertTrue(image.props.pixbuf)
