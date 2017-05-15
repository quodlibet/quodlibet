# -*- coding: utf-8 -*-
# Copyright 2017 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import GdkPixbuf

from tests import TestCase, get_data_path


class Timage_support(TestCase):
    """Mostly targeted at Windows/OSX, to make sure we package all the image
    decoders correctly
    """

    IMAGES = [
        "image.svg",
        "image.bmp",
        "image.png",
        "image.gif",
        "image.jpg",
    ]

    def test_create_pixbuf(self):
        for name in self.IMAGES:
            file_path = get_data_path(name)
            pb = GdkPixbuf.Pixbuf.new_from_file(file_path)
            assert pb
            assert pb.get_width() == 16
            assert pb.get_height() == 16
