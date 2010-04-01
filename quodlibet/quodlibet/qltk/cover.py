# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

import gobject
import gtk

from quodlibet import qltk
from quodlibet import stock
from quodlibet import config
from quodlibet import const
from quodlibet.util import thumbnails

class BigCenteredImage(qltk.Window):
    """Load an image and display it, scaling down to 1/2 the screen's
    dimensions if necessary.

    This might leak memory, but it could just be Python's GC being dumb."""

    def __init__(self, title, filename, parent=None):
        super(BigCenteredImage, self).__init__()
        self.set_transient_for(qltk.get_top_parent(parent))
        width = gtk.gdk.screen_width() / 2
        height = gtk.gdk.screen_height() / 2

        pixbuf = gtk.gdk.pixbuf_new_from_file(filename)
        pixbuf = thumbnails.scale(pixbuf, (width, height), scale_up=False)

        self.set_title(title)
        self.set_decorated(False)
        self.set_position(gtk.WIN_POS_CENTER)
        self.set_modal(False)
        self.set_icon(pixbuf)
        self.add(gtk.Frame())
        self.child.set_shadow_type(gtk.SHADOW_OUT)
        self.child.add(gtk.EventBox())
        self.child.child.add(gtk.Image())
        self.child.child.child.set_from_pixbuf(pixbuf)

        self.child.child.connect('button-press-event', self.__destroy)
        self.child.child.connect('key-press-event', self.__destroy)
        self.show_all()

    def __destroy(self, *args):
        self.destroy()

class ResizeImage(gtk.Image):
    """Automatically resizes to the maximum height given by it's
    parent container. If resize is True, size and max will be ignored"""
    def __init__(self, resize, size=0, max=128):
        super(ResizeImage, self).__init__()
        self.__path = None
        self.__ignore = False
        self.__resize = resize
        self.__size = size
        self.__max_size = max
        self.__no_cover = None
        if self.__resize:
            self.set_size_request(-1, 0)
            self.connect("size-allocate", self.__allocate)

    def set_path(self, path):
        if path != self.__path:
            self.__path = path
            if self.__resize:
                self.queue_resize()
            else:
                self.__update_image()

    def __allocate(self, img, alloc):
        self.__size = alloc.height - 2
        if not self.__ignore:
            self.__update_image()

    def __get_no_cover(self, width, height):
        if self.__no_cover is None or self.__no_cover.get_width() != width \
            or self.__no_cover.get_height() != height:
            icon = os.path.join(const.IMAGEDIR, stock.NO_COVER)
            try:
                self.__no_cover = gtk.gdk.pixbuf_new_from_file_at_size(
                    icon + ".svg", width, height)
            except gobject.GError:
                self.__no_cover = gtk.gdk.pixbuf_new_from_file_at_size(
                    icon + ".png", width, height)
        return self.__no_cover

    def __update_image(self):
        height = self.__size
        if not height: return

        if self.__resize:
            height = min(self.__max_size, height)
            width = self.__max_size
        else:
            width = height

        if self.__path is None:
            pixbuf = self.__get_no_cover(width, height)
        else:
            try:
                round_thumbs = config.getboolean("settings", "round")
                pixbuf = thumbnails.get_thumbnail(self.__path, (width, height))
                pixbuf = thumbnails.add_border(pixbuf, 80, round_thumbs)
            except gobject.GError:
                pixbuf = self.__get_no_cover(width, height)

        self.set_from_pixbuf(pixbuf)
        if self.__resize:
            self.__ignore = True
            self.__sig = self.connect_after("size-allocate",
                self.__stop_ignore)

    def __stop_ignore(self, *args):
        self.__ignore = False
        self.disconnect(self.__sig)

class CoverImage(gtk.EventBox):
    __albumfn = None
    __current_bci = None

    def __init__(self, resize=False, size=70, song=None):
        super(CoverImage, self).__init__()
        self.add(ResizeImage(resize, size))
        self.connect('button-press-event', self.__show_cover)
        self.set_song(self, song)
        self.show_all()

    def set_song(self, activator, song):
        if not self.child: return
        if song:
            cover = song.find_cover()
            self.__albumfn = cover and cover.name
            self.child.set_path(self.__albumfn)
        else:
            self.child.set_path(None)
        self.__song = song

    def __nonzero__(self):
        return bool(self.__albumfn)

    def __reset_bci(self, bci):
        self.__current_bci = None

    def __show_cover(self, box, event):
        """Show the cover as a detached BigCenteredImage.
        If one is already showing, destroy it instead"""
        if (self.__song and event.button == 1 and self.__albumfn and
            event.type == gtk.gdk.BUTTON_PRESS):
            if self.__current_bci is None:
                # We're not displaying it yet; display it.
                self.__current_bci = BigCenteredImage(
                    self.__song.comma("album"), self.__albumfn, self)
                self.__current_bci.connect('destroy', self.__reset_bci)
            else:
                # We're displaying it; destroy it.
                self.__current_bci.destroy()
