# -*- coding: utf-8 -*-
# Copyright 2009-2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import tempfile
import hashlib

from gi.repository import GdkPixbuf, GLib

from quodlibet.const import USERDIR
from quodlibet.util.path import mtime, mkdir, pathname2url, \
    xdg_get_cache_home, is_fsnative
from quodlibet.qltk.image import scale


def get_thumbnail_folder():
    """Returns a path to the thumbnail folder.

    The returned path might not exist.
    """

    if os.name == "nt":
        thumb_folder = os.path.join(USERDIR, "thumbnails")
    else:
        cache_folder = os.path.join(xdg_get_cache_home(), "thumbnails")
        thumb_folder = os.path.expanduser('~/.thumbnails')
        if os.path.exists(cache_folder) or not os.path.exists(thumb_folder):
            thumb_folder = cache_folder

    return thumb_folder


def get_cache_info(path, boundary):
    """For an image at `path` return (cache_path, thumb_size)

    cache_path points to a potential cache file
    thumb size is either 128 or 256
    """

    assert is_fsnative(path)

    width, height = boundary

    if width <= 128 and height <= 128:
        size_name = "normal"
        thumb_size = 128
    else:
        size_name = "large"
        thumb_size = 256

    thumb_folder = get_thumbnail_folder()
    cache_dir = os.path.join(thumb_folder, size_name)

    uri = "file://" + pathname2url(path)
    thumb_name = hashlib.md5(uri).hexdigest() + ".png"
    thumb_path = os.path.join(cache_dir, thumb_name)

    return (thumb_path, thumb_size)


def get_thumbnail_from_file(fileobj, boundary):
    """Like get_thumbnail() but works with files that can't be reopened.

    This is needed on Windows where NamedTemporaryFile can't be reopened.

    Returns Pixbuf or None.
    """

    assert fileobj

    try:
        path = fileobj.name
        assert is_fsnative(path), path
        return get_thumbnail(path, boundary)
    except GLib.GError:
        try:
            loader = GdkPixbuf.PixbufLoader()
            loader.write(fileobj.read())
            loader.close()
            fileobj.seek(0, 0)
            # can return None in case of partial data
            pixbuf = loader.get_pixbuf()
        except (GLib.GError, EnvironmentError):
            pass
        else:
            if pixbuf is not None:
                return scale(pixbuf, boundary)


def get_thumbnail(path, boundary):
    """Get a thumbnail pixbuf of an image at `path`.

    Will create/use a thumbnail in the user's thumbnail directory if possible.
    Follows the Free Desktop specification:

    http://specifications.freedesktop.org/thumbnail-spec/

    Can raise GLib.GError.
    """

    width, height = boundary

    # embedded thumbnails come from /tmp/
    # and too big thumbnails make no sense
    if path.startswith(tempfile.gettempdir()) or \
            width > 256 or height > 256 or mtime(path) == 0:
        return GdkPixbuf.Pixbuf.new_from_file_at_size(path, width, height)

    thumb_path, thumb_size = get_cache_info(path, boundary)
    cache_dir = os.path.dirname(thumb_path)
    try:
        mkdir(cache_dir, 0700)
    except OSError:
        return GdkPixbuf.Pixbuf.new_from_file_at_size(path, width, height)

    pb = meta_mtime = None
    if os.path.exists(thumb_path):
        try:
            pb = GdkPixbuf.Pixbuf.new_from_file(thumb_path)
        except GLib.GError:
            # in case it fails to load, we recreate it
            pass
        else:
            meta_mtime = pb.get_option("tEXt::Thumb::MTime")
            if meta_mtime:
                try:
                    meta_mtime = int(meta_mtime)
                except ValueError:
                    pass

    if not pb or meta_mtime != int(mtime(path)):
        pb = GdkPixbuf.Pixbuf.new_from_file(path)

        #Too small picture, no thumbnail needed
        if pb.get_width() < thumb_size and pb.get_height() < thumb_size:
            return scale(pb, boundary)

        info = GdkPixbuf.Pixbuf.get_file_info(path)[0]
        uri = "file://" + pathname2url(path)
        mime = info.get_mime_types()[0]
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
        pb.savev(thumb_path, "png", options.keys(), options.values())
        try:
            os.chmod(thumb_path, 0600)
        except OSError:
            pass

    return scale(pb, boundary)
