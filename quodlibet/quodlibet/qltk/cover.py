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

from quodlibet import stock

class BigCenteredImage(gtk.Window):
    """Load an image and display it, scaling down to 1/2 the screen's
    dimensions if necessary.

    This might leak memory, but it could just be Python's GC being dumb."""

    def __init__(self, title, filename):
        super(BigCenteredImage, self).__init__()
        width = gtk.gdk.screen_width() / 2
        height = gtk.gdk.screen_height() / 2
        pixbuf = gtk.gdk.pixbuf_new_from_file(filename)

        x_rat = pixbuf.get_width() / float(width)
        y_rat = pixbuf.get_height() / float(height)
        if x_rat > 1 or y_rat > 1:
            if x_rat > y_rat: height = int(pixbuf.get_height() / x_rat)
            else: width = int(pixbuf.get_width() / y_rat)
            pixbuf = pixbuf.scale_simple(
                width, height, gtk.gdk.INTERP_BILINEAR)

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

    def __destroy(self, *args): self.destroy()

class CoverImage(gtk.Frame):
    __albumfn = None
    __current_bci = None
    __no_album = None

    def __init__(self, size=None, song=None):
        super(CoverImage, self).__init__()
        self.add(gtk.EventBox())
        self.child.add(gtk.Image())
        self.__size = size or [100, 71]
        self.child.connect('button-press-event', self.__show_cover)
        self.child.show_all()

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
            self.child.child.set_from_pixbuf(None)
            self.__albumfn = None
            self.hide()
        else:
            cover = song.find_cover()
            if cover is None:
                self.__albumfn = None
                self.child.child.set_from_pixbuf(self.__no_album)
            elif cover.name != self.__albumfn:
                try:
                    pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(
                        cover.name, *self.__size)
                except gobject.GError:
                    self.hide()
                else:
                    self.child.child.set_from_pixbuf(pixbuf)
                    self.__albumfn = cover.name
                    self.show()

    def show(self):
        if self.__albumfn:
            super(CoverImage, self).show()

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
