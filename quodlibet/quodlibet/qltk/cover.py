# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gobject
import gtk

from quodlibet import stock, config
from quodlibet.util import thumbnails

class BigCenteredImage(gtk.Window):
    """Load an image and display it, scaling down to 1/2 the screen's
    dimensions if necessary.

    This might leak memory, but it could just be Python's GC being dumb."""

    def __init__(self, title, filename):
        super(BigCenteredImage, self).__init__()
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

class CoverImage(gtk.EventBox):
    __albumfn = None
    __current_bci = None
    __no_album = None

    def __init__(self, size=None, song=None):
        super(CoverImage, self).__init__()
        self.add(gtk.Image())
        self.__size = size or [100, 71]
        self.connect('button-press-event', self.__show_cover)
        self.show_all()

        if self.__no_album is None:
            try:
                CoverImage.__no_album = gtk.gdk.pixbuf_new_from_file_at_size(
                    stock.NO_ALBUM, *self.__size)
            except RuntimeError:
                pass

        self.set_song(self, song)

    def set_song(self, activator, song):
        self.__song = song
        if song is None:
            # Sometimes called during shutdown when the child have
            # already been destroyed.
            if self.child:
                self.child.set_from_pixbuf(None)
            self.__albumfn = None
            self.hide()
        else:
            cover = song.find_cover()
            if cover is None:
                self.__albumfn = None
                self.child.set_from_pixbuf(self.__no_album)
            elif cover.name != self.__albumfn:
                try:
                    round_thumbs = config.getboolean("settings", "round")
                    pixbuf = thumbnails.get_thumbnail(cover.name, self.__size)
                    pixbuf = thumbnails.add_border(pixbuf, 80, round_thumbs)
                except gobject.GError:
                    self.child.set_from_pixbuf(self.__no_album)
                else:
                    self.child.set_from_pixbuf(pixbuf)
                    self.__albumfn = cover.name
            self.show()

    def __nonzero__(self):
        return bool(self.__albumfn)

    def __reset_bci(self, bci):
        self.__current_bci = None

    def __show_cover(self, box, event):
        """Show the cover as a detached BigCenteredImage.
        If one is already showing, destroy it instead"""
        if (self.__song and event.button == 1 and
            event.type == gtk.gdk.BUTTON_PRESS):
            if self.__current_bci is None:
                # We're not displaying it yet; display it.
                cover = self.__song.find_cover()
                if cover:
                    self.__current_bci = BigCenteredImage(
                        self.__song.comma("album"), cover.name)
                    self.__current_bci.connect('destroy', self.__reset_bci)
            else:
                # We're displaying it; destroy it.
                self.__current_bci.destroy()
