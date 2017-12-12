# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

from gi.repository import Gtk, GdkPixbuf, Gdk

from tests import TestCase, mkstemp, init_fake_app, destroy_fake_app
from quodlibet import config
from quodlibet.formats import AudioFile
from quodlibet.qltk.cover import (CoverImage, BigCenteredImage, ResizeImage,
    get_no_cover_pixbuf)


class TCoverImage(TestCase):
    def setUp(self):
        config.init()
        init_fake_app()
        fd, self.fn = mkstemp()
        os.close(fd)
        pb = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 150, 10)
        pb.savev(self.fn, "png", [], [])

    def tearDown(self):
        destroy_fake_app()
        config.quit()
        os.remove(self.fn)

    def test_set_song(self):
        c = CoverImage()
        c.set_song(AudioFile({"~filename": "woo"}))
        event = Gdk.Event.new(Gdk.EventType.BUTTON_PRESS)
        event.type.button = 1
        c.emit("button-press-event", event)
        c.destroy()

    def test_big_window(self):
        parent = Gtk.Window()
        w = BigCenteredImage("foobar", open(self.fn, "rb"), parent)
        w.destroy()

    def test_resize(self):
        w = ResizeImage(False)
        w.set_file(open(self.fn, "rb"))
        w.set_file(None)
        w.destroy()

    def test_no_cover(self):
        pb = get_no_cover_pixbuf(5, 10)
        self.assertEqual(pb.get_width(), 5)
        self.assertEqual(pb.get_height(), 5)

        pb = get_no_cover_pixbuf(10, 5)
        self.assertEqual(pb.get_width(), 5)
        self.assertEqual(pb.get_height(), 5)
