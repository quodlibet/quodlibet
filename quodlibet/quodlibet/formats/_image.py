# -*- coding: utf-8 -*-
# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation


class ImageContainer(object):
    """Mixin/Interface for AudioFile to support basic embedded image editing"""

    def get_primary_image(self):
        """Returns the primary embedded image or None."""

        return

    @property
    def has_images(self):
        """Fast way to check for images, might be False if the file
        was modified externally.
        """

        return "~picture" in self

    @has_images.setter
    def has_images(self, value):
        if value:
            self["~picture"] = "y"
        else:
            self.pop("~picture", None)

    @property
    def can_change_images(self):
        """Return True IFF `clear_images()` and `set_images()` are
        implemented"""

        return False

    def clear_images(self):
        """Delete all embedded images"""

        raise NotImplementedError

    def set_image(self, image):
        """Replaces all embedded images by the passed image"""

        raise NotImplementedError


class EmbeddedImage(object):
    """Embedded image, contains most of the properties needed
    for FLAC and ID3 images.
    """

    def __init__(self, mime_type, width, height, color_depth, fileobj):
        self.mime_type = mime_type
        self.width = width
        self.height = height
        self.color_depth = color_depth
        self.file = fileobj

    def __repr__(self):
        return "<%s mime_type=%r width=%d height=%d file=%r>" % (
            type(self).__name__, self.mime_type, self.width, self.height,
            self.file)

    @classmethod
    def from_path(cls, path):
        """Reads the header of `path` and creates a new image instance
        or None.
        """

        from gi.repository import GdkPixbuf, GLib

        pb = []

        # Feed data to PixbufLoader until it emits area-prepared,
        # get the partially filled pixbuf and extract the needed
        # information.

        def area_prepared(loader):
            pb.append(loader.get_pixbuf())

        loader = GdkPixbuf.PixbufLoader()
        loader.connect("area-prepared", area_prepared)

        try:
            with open(path, "rb") as h:
                while not pb:
                    data = h.read(1024)
                    if data:
                        loader.write(data)
                    else:
                        break
        except EnvironmentError:
            return
        finally:
            try:
                loader.close()
            except GLib.GError:
                pass

        if not pb:
            return

        pb = pb[0]

        width = pb.get_width()
        height = pb.get_height()
        color_depth = pb.get_bits_per_sample()

        format_ = loader.get_format()
        mime_types = format_.get_mime_types()
        mime_type = mime_types and mime_types[0] or ""

        try:
            return cls(mime_type, width, height, color_depth, open(path, "rb"))
        except EnvironmentError:
            return


class APICType(object):
    """Enumeration of image types defined by the ID3 standard but also reused
    in WMA/FLAC/VorbisComment
    """

    # Other
    OTHER = 0
    # 32x32 pixels 'file icon' (PNG only)
    FILE_ICON = 1
    # Other file icon
    OTHER_FILE_ICON = 2
    # Cover (front)
    COVER_FRONT = 3
    # Cover (back)
    COVER_BACK = 4
    # Leaflet page
    LEAFLET_PAGE = 5
    # Media (e.g. label side of CD)
    MEDIA = 6
    # Lead artist/lead performer/soloist
    LEAD_ARTIST = 7
    # Artist/performer
    ARTIST = 8
    # Conductor
    CONDUCTOR = 9
    # Band/Orchestra
    BAND = 10
    # Composer
    COMPOSER = 11
    # Lyricist/text writer
    LYRISCIST = 12
    # Recording Location
    RECORDING_LOCATION = 13
    # During recording
    DURING_RECORDING = 14
    # During performance
    DURING_PERFORMANCE = 15
    # Movie/video screen capture
    SCREEN_CAPTURE = 16
    # A bright coloured fish
    FISH = 17
    # Illustration
    ILLUSTRATION = 18
    # Band/artist logotype
    BAND_LOGOTYPE = 19
    # Publisher/Studio logotype
    PUBLISHER_LOGOTYPE = 20

    @classmethod
    def is_valid(cls, value):
        return cls.OTHER <= value <= cls.PUBLISHER_LOGOTYPE

    @classmethod
    def sort_key(cls, value):
        """Sorts picture types, most important picture is the highest.
        Important is defined as most representative of an album release, ymmv.
        """

        # index value -> important
        important = [
            cls.LEAFLET_PAGE, cls.MEDIA,
            cls.COVER_BACK, cls.COVER_FRONT
        ]

        try:
            return important.index(value)
        except ValueError:
            if value < cls.COVER_FRONT:
                return value - 100
            else:
                return -value
