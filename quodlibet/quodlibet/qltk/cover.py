# -*- coding: utf-8 -*-
# Copyright 2004-2011 Joe Wreschnig, Michael Urman, Iñigo Serna,
# Christoph Reiter, Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, GLib, Gdk, GdkPixbuf

from quodlibet import qltk
from quodlibet import config
from quodlibet.util import thumbnails


# TODO: neater way of managing dependency on this particular plugin
ALBUM_ART_PLUGIN_ID = "Download Album art"


class BigCenteredImage(qltk.Window):
    """Load an image and display it, scaling down to 1/2 the screen's
    dimensions if necessary.

    This might leak memory, but it could just be Python's GC being dumb."""

    def __init__(self, title, filename, parent=None):
        super(BigCenteredImage, self).__init__()
        self.set_transient_for(qltk.get_top_parent(parent))
        width = Gdk.Screen.width() / 2
        height = Gdk.Screen.height() / 2

        pixbuf = GdkPixbuf.Pixbuf.new_from_file(filename)
        pixbuf = thumbnails.scale(pixbuf, (width, height), scale_up=False)

        self.set_title(title)
        self.set_decorated(False)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_modal(False)

        image = Gtk.Image()
        image.set_from_pixbuf(pixbuf)

        event_box = Gtk.EventBox()
        event_box.add(image)

        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.OUT)
        frame.add(event_box)

        self.add(frame)

        event_box.connect('button-press-event', self.__destroy)
        event_box.connect('key-press-event', self.__destroy)
        self.get_child().show_all()

    def __destroy(self, *args):
        self.destroy()


def get_no_cover_pixbuf(width, height):
    size = max(width, height)
    theme = Gtk.IconTheme.get_default()
    try:
        no_cover = theme.load_icon("quodlibet-missing-cover", size, 0)
    except GLib.GError:
        return
    else:
        return thumbnails.scale(no_cover, (width, height))


class ResizeImage(Gtk.DrawingArea):
    def __init__(self, resize=False, size=1):
        Gtk.DrawingArea.__init__(self)
        self._dirty = True
        self._path = None
        self._pixbuf = None
        self._no_cover = None
        self._size = size
        self._resize = resize

    def set_path(self, path):
        if self._path == path:
            return

        self._path = path
        self._dirty = True
        self.queue_resize()

    def _get_pixbuf(self):
        if not self._dirty:
            return self._pixbuf

        self._dirty = False

        if self._path is None:
            self._pixbuf = get_no_cover_pixbuf(256, 256)
            return self._pixbuf

        try:
            self._pixbuf = thumbnails.get_thumbnail(self._path, (256, 256))
        except GLib.GError:
            pass
        else:
            return self._pixbuf

    def _get_size(self, max_width, max_height):
        pixbuf = self._get_pixbuf()
        if not pixbuf:
            return 0, 0
        width, height = pixbuf.get_width(), pixbuf.get_height()
        return thumbnails.calc_scale_size(
                (max_width, max_height),
                (width, height))

    def do_get_request_mode(self):
        if self._resize:
            return Gtk.SizeRequestMode.HEIGHT_FOR_WIDTH
        return Gtk.SizeRequestMode.CONSTANT_SIZE

    def do_get_preferred_width(self):
        if self._resize:
            return (0, 0)
        else:
            width, height = self._get_size(self._size, self._size)
            return (width, width)

    def do_get_preferred_height(self):
        if self._resize:
            return (0, 0)
        else:
            width, height = self._get_size(self._size, self._size)
            return (height, height)

    def do_get_preferred_width_for_height(self, req_height):
        width, height = self._get_size(300, req_height)

        if width > 256:
            width = width

        return (width, width)

    def do_draw(self, cairo_context):
        pixbuf = self._get_pixbuf()
        if not pixbuf:
            return

        alloc = self.get_allocation()
        width, height = alloc.width, alloc.height
        if self._path:
            if width < 2 or height < 2:
                return
            round_thumbs = config.getboolean("albumart", "round")
            pixbuf = thumbnails.scale(pixbuf, (width - 2, height - 2))
            pixbuf = thumbnails.add_border(pixbuf, 80, round_thumbs)
        else:
            pixbuf = thumbnails.scale(pixbuf, (width, height))

        style_context = self.get_style_context()
        Gtk.render_icon(style_context, cairo_context, pixbuf, 0, 0)


class CoverImage(Gtk.EventBox):

    def __init__(self, resize=False, size=70, song=None):
        super(CoverImage, self).__init__()
        self.__song = None
        self.__file = None
        self.__current_bci = None

        self.add(ResizeImage(resize, size))
        self.connect('button-press-event', self.__show_cover)
        self.set_song(song)
        self.get_child().show_all()

    def set_song(self, song):
        self.__song = song
        if song:
            self.__file = song.find_cover()
            self.get_child().set_path(self.__file and self.__file.name)
        else:
            self.__file = None
            self.get_child().set_path(None)

    def refresh(self):
        self.set_song(self.__song)

    def __nonzero__(self):
        return bool(self.__file)

    def __reset_bci(self, bci):
        self.__current_bci = None

    def __show_cover(self, box, event):
        """Show the cover as a detached BigCenteredImage.
        If one is already showing, destroy it instead
        If there is no image, run the AlbumArt plugin
        """

        song = self.__song
        if not song:
            return

        if event.button != Gdk.BUTTON_PRIMARY or \
                event.type != Gdk.EventType.BUTTON_PRESS:
            return

        if not self.__file:
            from quodlibet.qltk.songsmenu import SongsMenu
            from quodlibet import app

            SongsMenu.plugins.handle("Download Album art", app.library,
                                     qltk.get_top_parent(self), [song])
            return True

        if self.__current_bci is not None:
            # We're displaying it; destroy it.
            self.__current_bci.destroy()
            return True

        try:
            self.__current_bci = BigCenteredImage(
                song.comma("album"), self.__file.name, parent=self)
        except GLib.GError: # reload in case the image file is gone
            self.refresh()
        else:
            self.__current_bci.show()
            self.__current_bci.connect('destroy', self.__reset_bci)

        return True
