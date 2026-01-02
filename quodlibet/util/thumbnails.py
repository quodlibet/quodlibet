# Copyright 2009-2014 Christoph Reiter
#             2021-23 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import hashlib
from pathlib import Path
from tempfile import gettempdir

from gi.repository import GdkPixbuf, GLib

from quodlibet import print_w, print_d
from senf import fsn2uri, fsnative

import quodlibet
from quodlibet.util.path import mtime, mkdir, xdg_get_cache_home
from quodlibet.util import enum
from quodlibet.qltk.image import scale


def get_thumbnail_folder() -> Path:
    """Returns a path to the thumbnail folder.

    The returned path might not exist.
    """

    if os.name == "nt":
        thumb_folder = Path(quodlibet.get_cache_dir()) / "thumbnails"
    else:
        cache_folder = Path(xdg_get_cache_home()) / "thumbnails"
        thumb_folder = Path("~/.thumbnails").expanduser()
        if cache_folder.exists() or not thumb_folder.exists():
            thumb_folder = cache_folder

    return thumb_folder


@enum
class ThumbSize(int):
    NORMAL = 128
    LARGE = 256
    LARGEST = LARGE


def get_cache_info(path: Path, boundary: tuple[int, int]) -> tuple[Path, int]:
    """For an image at `path` return (cache_path, thumb_size)

    cache_path points to a potential cache file
    thumb size is either 128 or 256
    """

    width, height = boundary

    if width <= ThumbSize.NORMAL and height <= ThumbSize.NORMAL:
        size_name = "normal"
        thumb_size = ThumbSize.NORMAL
    else:
        size_name = "large"
        thumb_size = ThumbSize.LARGE

    thumb_folder = get_thumbnail_folder()
    cache_dir = thumb_folder / size_name

    uri = fsn2uri(str(path))
    thumb_name = hashlib.md5(uri.encode("ascii")).hexdigest() + ".png"
    thumb_path = cache_dir / thumb_name

    return thumb_path, thumb_size


def get_thumbnail_from_file(fileobj, boundary) -> GdkPixbuf.Pixbuf | None:
    """Like get_thumbnail() but works with files that can't be reopened.

    This is needed on Windows where NamedTemporaryFile can't be reopened.

    :returns: Pixbuf or None. Thread-safe.
    """

    assert fileobj

    path = fileobj.name
    assert isinstance(path, fsnative), path
    try:
        return get_thumbnail(path, boundary)
    except GLib.GError as e:
        print_d(f"Failed getting thumbnail from file ({e}), trying PixbufLoader")
        try:
            loader = GdkPixbuf.PixbufLoader()
            loader.set_size(*boundary)
            loader.write(fileobj.read())
            loader.close()
            fileobj.seek(0, 0)
            # can return None in case of partial data
            return loader.get_pixbuf()
        except (OSError, GLib.GError) as e:
            print_w(f"Couldn't load thumbnail at {path} from Pixbufloader ({e})")
    return None


def get_thumbnail(path: fsnative, boundary, ignore_temp=True) -> GdkPixbuf:
    """Get a thumbnail pixbuf of an image at `path`.

    Will create/use a thumbnail in the user's thumbnail directory if possible.
    Follows the Free Desktop specification:

    http://specifications.freedesktop.org/thumbnail-spec/

    If ignore_temp then no thumbnail cache will be created for files
    in the default temporary directory.

    Can raise GLib.GError. Thread-safe.
    """

    assert isinstance(path, fsnative), type(path)

    width, height = boundary
    new_from_file_at_size = GdkPixbuf.Pixbuf.new_from_file_at_size

    # larger than thumbnails, load directly
    if width > ThumbSize.LARGEST or height > ThumbSize.LARGEST:
        return new_from_file_at_size(path, width, height)

    path_mtime = mtime(path)
    if path_mtime == 0:
        return new_from_file_at_size(path, width, height)

    # embedded thumbnails come from /tmp/
    # FIXME: move this to another layer
    if ignore_temp and path.startswith(gettempdir()):
        return new_from_file_at_size(path, width, height)

    thumb_path, thumb_size = get_cache_info(Path(path), boundary)
    cache_dir = thumb_path.parent
    try:
        mkdir(cache_dir, 0o700)
    except OSError as e:
        print_w(f"Couldn't create cache dir {cache_dir!r} ({e}")
        return new_from_file_at_size(path, width, height)

    try:
        pb = new_from_file_at_size(str(thumb_path), width, height)
    except GLib.GError:
        # in case it fails to load, we recreate it
        print_d(f"Couldn't find thumbnail at {str(thumb_path)!r}, so recreating.")
    else:
        meta_mtime = pb.get_option("tEXt::Thumb::MTime")
        if meta_mtime is not None:
            try:
                meta_mtime = int(meta_mtime)
            except ValueError:
                pass
            else:
                if meta_mtime == int(path_mtime):
                    return pb

    info, pw, ph = GdkPixbuf.Pixbuf.get_file_info(path)

    # Too small picture, no thumbnail needed
    if pw < thumb_size and ph < thumb_size:
        return new_from_file_at_size(path, width, height)

    thumb_pb = new_from_file_at_size(path, thumb_size, thumb_size)

    uri = fsn2uri(path)
    mime = info.get_mime_types()[0]
    options = {
        "tEXt::Thumb::Image::Width": str(pw),
        "tEXt::Thumb::Image::Height": str(ph),
        "tEXt::Thumb::URI": uri,
        "tEXt::Thumb::MTime": str(int(path_mtime)),
        "tEXt::Thumb::Size": str(os.path.getsize(path)),
        "tEXt::Thumb::Mimetype": mime,
        "tEXt::Software": "QuodLibet",
    }

    print_d(f"Saving thumbnail to {thumb_path!s}")
    thumb_pb.savev(str(thumb_path), "png", list(options.keys()), list(options.values()))
    try:
        thumb_path.chmod(0o600)
    except OSError:
        pass

    return scale(thumb_pb, boundary)
