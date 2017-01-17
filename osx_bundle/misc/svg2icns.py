#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""
./svg2icns.py source.svg target.icns
"""

import sys
import struct

from gi.repository import GdkPixbuf


def get_png(svg_path, size):
    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
        svg_path, size, size, True)
    return pixbuf.save_to_bufferv("png", ["compression"], ["9"])[1]


def get_icon(svg_path, size):
    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
        svg_path, size, size, True)
    data = bytearray(pixbuf.get_pixels())

    channels = pixbuf.get_n_channels()
    assert channels == 4

    # https://en.wikipedia.org/wiki/PackBits
    # no real compression going on here..
    new_data = bytearray()
    for c in xrange(3):
        x = 0
        for i in xrange(0, len(data), 4):
            if x == 0 or x % 128 == 0:
                new_data.append(127)
            new_data.append(data[i+c])
            x += 1

    return new_data


def get_mask(svg_path, size):
    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
        svg_path, size, size, True)
    data = bytearray(pixbuf.get_pixels())

    channels = pixbuf.get_n_channels()
    assert channels == 4

    new_data = bytearray()
    for i in xrange(0, len(data), 4):
        new_data.append(data[i+3])

    return new_data


def get_icns(svg_path):
    # https://en.wikipedia.org/wiki/Apple_Icon_Image_format
    # Note icp4/5 png don't work under OSX. Maybe Wikipedia is wrong.

    ICONS = [
        (b"is32", 16, "icon"),
        (b"s8mk", 16, "mask"),
        (b"il32", 32, "icon"),
        (b"l8mk", 32, "mask"),
        (b"ic08", 256, "png"),
        (b"ic09", 512, "png"),
        (b"icp6", 64, "png"),
        (b"ic07", 128, "png"),
        # seems unnecessarily large for now..
        # (b"ic10", 1024, "png"),
        (b"ic11", 32, "png"),
        (b"ic12", 64, "png"),
        (b"ic13", 256, "png"),
        (b"ic14", 512, "png"),
    ]

    funcs = {
        "png": get_png,
        "icon": get_icon,
        "mask": get_mask,
    }

    icons = {}
    for name, size, type_ in ICONS:
        key = (size, type_)
        if key not in icons:
            icons[key] = funcs[type_](svg_path, size)

    toc = bytearray(b"TOC ")
    toc += struct.pack(">I", 8 + len(ICONS) * 8)

    data = bytearray()
    for name, size, type_ in ICONS:
        key = (size, type_)
        data += name
        toc += name
        icon = icons[key]
        pack_size = struct.pack(">I", 8 + len(icon))
        data += pack_size
        toc += pack_size
        data += icon
    data[0:0] = toc

    header = bytearray()
    header += b"icns"
    header += struct.pack(">I", 8 + len(data))
    data[0:0] = header

    return data


def main(argv):
    svg = argv[1]
    dest = argv[2]

    with open(dest, "wb") as h:
        h.write(get_icns(svg))


if __name__ == "__main__":
    main(sys.argv)
