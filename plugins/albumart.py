#Copyright 2005 Eduardo Gonzalez, Niklas Janlert
#Amazon API code by Mark Pilgrim
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import sys
import urllib
import threading
from cStringIO import StringIO
import gtk
import gobject
import pango
import util
import qltk

if sys.version_info < (2, 4): from sets import Set as set

try:
    import amazon
except ImportError:
    qltk.ErrorMessage(None,
                      "Module not found",
                      "<b>Unable to load amazon.py</b>\n" +
                      "Please make sure amazon.py is in your plugins folder. "+
                      "A compatible version can be found in the Quod Libet " +
                      "Subversion repository.").run()

__all__ = ["plugin_album"]

PLUGIN_NAME = "Download Album art"
PLUGIN_DESC = "Downloads album covers from Amazon.com"
PLUGIN_ICON = gtk.STOCK_FIND
PLUGIN_VERSION = "0.20"

class AlbumArtWindow(gtk.Window):
    def __init__(self, songs):
        gtk.Window.__init__(self)
        self.set_border_width(12)
        self.set_title("AlbumArt")
        self.set_default_size(650, 350)
        
        #TreeView stuff
        self.liststore = liststore = gtk.ListStore(object, str)
        treeview = gtk.TreeView(liststore)
        treeview.set_headers_visible(False)
        selection = treeview.get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)
        selection.connect("changed", self.__preview)

        rend = gtk.CellRendererPixbuf()
        def cell_data(column, cell, model, iter):
            cell.set_property("pixbuf", model[iter][0]["thumb"])
        tvcol1 = gtk.TreeViewColumn("Pixbuf", rend)
        tvcol1.set_cell_data_func(rend, cell_data)
        tvcol1.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
        rend.set_property('xpad', 2)
        rend.set_property('ypad', 2)
        rend.set_property('width', 56)
        rend.set_property('height', 56)
        treeview.append_column(tvcol1)

        rend = gtk.CellRendererText()
        rend.set_property("ellipsize", pango.ELLIPSIZE_END)
        tvcol2 = gtk.TreeViewColumn("Info", rend, markup=1)
        treeview.append_column(tvcol2)

        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.add(treeview)

        #Image frame and save button
        self.image = image = gtk.Image()
        frame = gtk.Frame()
        frame.set_shadow_type(gtk.SHADOW_IN)
        frame.add(image)
        vbox = gtk.VBox(spacing=5)
        vbox.pack_start(frame)
        self.button = button = gtk.Button(stock=gtk.STOCK_SAVE)
        button.set_sensitive(False)
        fname = self.__get_fname(songs)
        def save_cb(button, fname):
            model, path = selection.get_selected()
            data = model[path][0]["cover_data"]
            self.__save_cover(data, fname)
        button.connect("clicked", save_cb, fname)
        bbox = gtk.HButtonBox()
        bbox.pack_start(button, expand=False, fill=False)
        bbox.set_layout(gtk.BUTTONBOX_SPREAD)
        vbox.pack_start(bbox, expand=False, fill=False)

        hpaned = gtk.HPaned()
        hpaned.pack1(sw)
        hpaned.pack2(vbox)
        hpaned.set_position(300)
        self.add(hpaned)

        thread = threading.Thread(target=self.__search, args=(songs,))
        thread.setDaemon(True)
        thread.start()

        self.show_all()
        
    def __search(self, songs):
        artist = songs[0]('artist')
        album = songs[0]('album')

        amazon.setLicense("0RKH4ZH1JCFZHMND91G2")

        try:
            bags = amazon.searchByKeyword(artist + '+' + album, type="lite", 
                                          product_line="music")
        except amazon.AmazonError, msg:
            def destroy_cb(dialog, response, self):
                dialog.destroy()
                self.destroy()
            def quick_error_helper(self, msg):
                dialog = qltk.Message(gtk.MESSAGE_ERROR, None, "Search error", 
                                      msg)
                dialog.connect('response', destroy_cb, self)
                dialog.show()
            gobject.idle_add(quick_error_helper, self, msg)
        else:
            # Just keep the top 10 matches
            for bag in bags[:10]:
                gobject.idle_add(self.__add_bag, self.liststore, bag)

    def __add_bag(self, model, bag):
        # Text part
        title = util.escape(getattr(bag, "ProductName", ""))
        artist = (getattr(bag, "Artists", None) and 
                  getattr(bag.Artists, "Artist", None) or "")
        if isinstance(artist, list):
            artist = ", ".join(artist)
        artist = util.escape(artist)
        if hasattr(bag, "ReleaseDate"):
            date = "(%s)" %util.escape(bag.ReleaseDate)
        else:
            date = ""
        markup = "<i><b>%s</b></i> %s\n%s" %(title, date, artist)

        # Image part
        sock = urllib.urlopen(bag.ImageUrlSmall)
        data = StringIO()
        item = {"bag": bag, "thumb": None, "thumb_data": ""}
        loader = gtk.gdk.PixbufLoader()
        w = h = 48
        loader.set_size(w, h)
        loader.connect("closed", self.__got_thumb_cb, data, item, w, h)

        gobject.io_add_watch(sock, gobject.IO_IN, self.__copy_image, loader, 
                             data)
        gobject.io_add_watch(sock, gobject.IO_ERR, self.__copy_err, loader)
        model.append([item, markup])

    def __got_thumb_cb(self, loader, data, item, w, h):
        item["thumb_data"] = data.getvalue()
        cover = loader.get_pixbuf()
        thumb = gtk.gdk.Pixbuf(
            gtk.gdk.COLORSPACE_RGB, True, 8, w + 2, h + 2)
        thumb.fill(0x000000ff)
        cover.copy_area(0, 0, w, h, thumb, 1, 1)
        item["thumb"] = thumb
        
    def __preview(self, selection):
        model, path = selection.get_selected()
        item = model[path][0]
        self.button.set_sensitive(False)
        
        if "cover" not in item:
            self.__get_cover(item, item["bag"].ImageUrlLarge)
        else:
            self.image.set_from_pixbuf(item["cover"])
            self.button.set_sensitive(True)

    def __get_cover(self, item, url):
        data = StringIO()
        sock = urllib.urlopen(url)
        loader = gtk.gdk.PixbufLoader()
        gobject.io_add_watch(sock, gobject.IO_IN, self.__copy_image, 
                             loader, data)
        gobject.io_add_watch(sock, gobject.IO_ERR, self.__copy_err, loader)
        loader.connect("closed", self.__got_cover_cb, data, item, url)
        loader.connect("area-updated", 
            lambda l, *a: self.image.set_from_pixbuf(l.get_pixbuf()))

    def __got_cover_cb(self, loader, data, item, url):
        cover = loader.get_pixbuf()
        # For some reason we get a 1x1 image if the given size didn't exist
        if cover.get_width() > item["thumb"].get_width():
            item["cover"] = cover
            item["cover_data"] = data.getvalue()
            self.image.set_from_pixbuf(item["cover"])
            self.button.set_sensitive(True)
        elif url == item["bag"].ImageUrlLarge:
            self.__get_cover(item, item["bag"].ImageUrlMedium)
        else:
            item["cover"] = item["thumb"]
            item["cover_data"] = item["thumb_data"]
            self.image.set_from_pixbuf(item["cover"])
            self.button.set_sensitive(True)

    def __copy_image(self, src, condition, loader, data):
        buf = src.read(256)
        if len(buf) > 0:
            loader.write(buf)
            data.write(buf)
            return True # Run again
        else:
            loader.close()
            src.close()
            return False # Stop

    def __copy_err(self, src, condition, loader):
        loader.close()

    def __save_cover(self, data, fname):
        if os.path.exists(fname) and not qltk.ConfirmAction(None, 
            "File exists", "The file <b>%s</b> already exists."
            "\n\nOverwrite?" %util.escape(fname)).run():
            return

        f = open(fname, "w")
        f.write(data)
        self.destroy()

    def __get_fname(self, songs):
        dirname = songs[0]("~dirname")
        fname = os.path.join(dirname, ".folder.jpg")
        #songsindir = library.query("~filename = /^%s/" % util.re_esc(dirname))
        #if len(songsindir) < len(songs):
        #    raise Exception #XXX
        #if len(songsindir) > len(songs):
        #    if "labelno" in songs[0]:
        #        fname = os.path.join(dirname, ".%(labelno)s.jpg" %songs[0]
        #    else:
        #        raise Exception #XXX
        #else:
        #    fname = os.path.join(dirname, ".folder.jpg")
        #    return 

        print "Will save to", fname
        return fname

    def PluginPreferences(parent):
        b = gtk.Button("Visit Amazon.com")
        b.connect('clicked', lambda s: util.website('http://www.amazon.com/'))
        return b

plugin_album = AlbumArtWindow
