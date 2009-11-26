# -*- coding: utf-8 -*-
# Copyright 2009 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import urllib
import tempfile

try:
  import hashlib as hash
except ImportError:
  import md5 as hash

import gobject
import gtk

from quodlibet.util import mtime

def add_border(pixbuf, val, round=False):
    """Add a 1px border to the pixbuf and round of the edges if needed.
    val is the border brightness from 0 to 255"""

    c = (val << 24) | (val << 16) | (val << 8) | 0xFF

    w, h = pixbuf.get_width(), pixbuf.get_height()
    newpb = gtk.gdk.Pixbuf(
        gtk.gdk.COLORSPACE_RGB, True, 8, w + 2, h + 2)
    newpb.fill(c)
    pixbuf.copy_area(0, 0, w, h, newpb, 1, 1)

    if round:
        m = ((0xFF - val) / 5) + val
        m = (m << 24) | (m << 16) | (m << 8) | 0xFF
        o = (c & 0xFFFFFF00) | 0x70
        n = (c & 0xFFFFFF00) | 0x40

        mask = (
            (0, 0, n, m),
            (0, o, m, 2),
            (n, m, 2, 2),
            (m, 2, 2, 2)
            )

        for y, row in enumerate(mask):
            for x, pix in enumerate(row):
                if pix != 2:
                    newpb.subpixbuf(x, y, 1, 1).fill(pix)
                    newpb.subpixbuf(w + 1 - x, y, 1, 1).fill(pix)
                    newpb.subpixbuf(w + 1 - x, h + 1 - y, 1, 1).fill(pix)
                    newpb.subpixbuf(x, h + 1 - y, 1, 1).fill(pix)

    return newpb

def calc_scale_size(boundary, size, scale_up=True):
    """Returns the biggest possible size to fit into the boundary,
    respecting the aspect ratio."""

    bwidth, bheight = boundary
    iwidth, iheight = size

    scale_w, scale_h = iwidth, iheight

    if iwidth > bwidth or iheight > bheight or scale_up:
        bratio = float(bwidth) / bheight
        iratio = float(iwidth) / iheight

        if iratio > bratio:
            scale_w = bwidth
            scale_h = int(bwidth / iratio)
        else:
            scale_w = int(bheight * iratio)
            scale_h = bheight

    return scale_w, scale_h

def scale(pixbuf, boundary, scale_up=True):
    """Scale a pixbuf so it fits into the boundary.
    (preserves image aspect ratio)"""

    size = pixbuf.get_width(), pixbuf.get_height()

    scale_w, scale_h = calc_scale_size(boundary, size, scale_up)

    return pixbuf.scale_simple(scale_w, scale_h, gtk.gdk.INTERP_BILINEAR)

def get_thumbnail(path, boundary):
    """Get a thumbnail of an image. Will create/use a thumbnail in
    the user's thumbnail directory if possible. Follows the
    Free Desktop specification. http://jens.triq.net/thumbnail-spec/"""

    width, height = boundary

    # embedded thumbnails come from /tmp/
    # and too big thumbnails make no sense
    if path.startswith(tempfile.gettempdir()) or \
        width > 256 or height > 256 or mtime(path) == 0:
        return gtk.gdk.pixbuf_new_from_file_at_size(path, width, height)

    thumb_folder = os.path.expanduser('~/.thumbnails')

    if not os.path.exists(thumb_folder):
        os.mkdir(thumb_folder)
        os.chmod(thumb_folder, 0700)

    if width <= 128 and height <= 128:
        size_name = "normal"
        thumb_size = 128
    else:
        size_name = "large"
        thumb_size = 256

    cache_dir = os.path.join(thumb_folder, size_name)

    if not os.path.exists(cache_dir):
        os.mkdir(cache_dir)
        os.chmod(cache_dir, 0700)

    uri = "file://" + urllib.pathname2url(path)
    thumb_name = hash.md5(uri).hexdigest() + ".png"

    thumb_path = os.path.join(cache_dir, thumb_name)

    pb = meta_mtime = None
    if os.path.exists(thumb_path):
        pb = gtk.gdk.pixbuf_new_from_file(thumb_path)
        meta_mtime = pb.get_option("tEXt::Thumb::MTime")
        meta_mtime = meta_mtime and int(meta_mtime)

    if not pb or meta_mtime != int(mtime(path)):
        pb = gtk.gdk.pixbuf_new_from_file(path)

        #Too small picture, no thumbnail needed
        if pb.get_width() < thumb_size and pb.get_height() < thumb_size:
            return scale(pb, boundary)

        mime = gtk.gdk.pixbuf_get_file_info(path)[0]['mime_types'][0]
        options = {
            "tEXt::Thumb::Image::Width": str(pb.get_width()),
            "tEXt::Thumb::Image::Height": str(pb.get_height()),
            "tEXt::Thumb::URI": uri,
            "tEXt::Thumb::MTime": str(int(mtime(path))),
            "tEXt::Thumb::Size": str(os.path.getsize(path)),
            "tEXt::Thumb::Mimetype": mime,
            "tEXt::Software": "QuodLibet"
            }

        pb = scale(pb, (thumb_size, thumb_size))
        pb.save(thumb_path, "png", options)
        os.chmod(thumb_path, 0600)

    return scale(pb, boundary)
