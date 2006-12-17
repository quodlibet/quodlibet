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
import config

from plugins.songsmenu import SongsMenuPlugin

if sys.version_info < (2, 4): from sets import Set as set

try:
    import amazon
except ImportError:
    import _amazon as amazon

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
        def save_cb(button, combo):
            model, path = selection.get_selected()
            data = model[path][0]["cover_data"]
            fname = self.__get_fname(songs, combo)
            self.__save_cover(data, fname)
        combo = gtk.combo_box_new_text()
        try: set_fn = config.get("plugins", "cover_fn")
        except: set_fn = ".folder.jpg"
        active = -1
        for i, fn in enumerate([".folder.jpg", "folder.jpg", "cover.jpg"]):
            combo.append_text(fn)
            if fn == set_fn: active = i
        if active == -1:
            combo.append_text(set_fn)
            combo.set_active(len(combo.get_model()) - 1)
        else: combo.set_active(active)
        button.connect("clicked", save_cb, combo)
        bbox = gtk.HButtonBox()
        bbox.pack_start(combo)
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
            query = songs[0]("artist") + " " + songs[0]("album")
            query = query.encode("latin1", 'replace')
            bags = amazon.searchByKeyword(
                query, type="lite", product_line="music")
        except amazon.AmazonError, msg:
            dialog = qltk.Message(gtk.MESSAGE_ERROR, None, "Search error", msg)
            dialog.connect('response', self.__destroy_cb)
            gobject.idle_add(dialog.show)
        except UnicodeEncodeError, msg:
            dialog = qltk.Message(gtk.MESSAGE_ERROR, None, "Encoding error", 
                                  msg)
            dialog.connect('response', self.__destroy_cb)
            gobject.idle_add(dialog.show)
        else:
            # Just keep the top 10 matches
            for bag in bags[:10]:
                gobject.idle_add(self.__add_bag, self.liststore, bag)

    def __destroy_cb(self, widget, *args):
        widget.destroy()
        self.destroy()

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

        item = {"bag": bag, "thumb": None, "thumb_data": ""}
        iter = model.append([item, markup])

        # Image part
        urlinfo = urllib.urlopen(bag.ImageUrlSmall)
        sock = urlinfo.fp._sock
        sock.setblocking(0)
        data = StringIO()

        loader = gtk.gdk.PixbufLoader()
        loader.connect("closed", self.__got_thumb_cb, data, item, model, iter)

        gobject.io_add_watch(
            sock, gobject.IO_IN | gobject.IO_ERR | gobject.IO_HUP, 
            self.__copy_image, loader, data)

    def __got_thumb_cb(self, loader, data, item, model, iter):
        cover = loader.get_pixbuf()
        if cover.get_width() > 1:
            w = h = 48
            cover = cover.scale_simple(w, h, gtk.gdk.INTERP_NEAREST)
            thumb = gtk.gdk.Pixbuf(
                gtk.gdk.COLORSPACE_RGB, True, 8, w + 2, h + 2)
            thumb.fill(0x000000ff)
            cover.copy_area(0, 0, w, h, thumb, 1, 1)
            item["thumb"] = thumb
            item["thumb_data"] = data.getvalue()
            model.row_changed(model.get_path(iter), iter)
        
    def __preview(self, selection):
        model, path = selection.get_selected()
        item = model[path][0]
        self.image.hide()
        self.button.set_sensitive(False)
        
        if item["thumb"]: # If there exists no thumbnail, then nothing bigger.
            if "cover" not in item:
                self.__get_cover(item, item["bag"].ImageUrlLarge)
            else:
                self.image.set_from_pixbuf(item["cover"])
                self.image.show()
                self.button.set_sensitive(True)

    def __get_cover(self, item, url):
        data = StringIO()
        urlinfo = urllib.urlopen(url)
        sock = urlinfo.fp._sock
        sock.setblocking(0)
        loader = gtk.gdk.PixbufLoader()
        gobject.io_add_watch(
            sock, gobject.IO_IN | gobject.IO_ERR | gobject.IO_HUP, 
            self.__copy_image, loader, data)
        loader.connect("closed", self.__got_cover_cb, data, item, url)
        def update(loader, x, y, w, h, image):
            if (w, h) > (1, 1):
                image.set_from_pixbuf(loader.get_pixbuf())
                image.show()
        loader.connect("area-updated", update, self.image)

    def __got_cover_cb(self, loader, data, item, url):
        cover = loader.get_pixbuf()
        # For some reason we get a 1x1 image if the given size didn't exist
        if cover.get_width() > 1:
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
        if condition in (gobject.IO_ERR, gobject.IO_HUP):
            loader.close()
            src.close()
            return False
        else: # Read
            buf = src.recv(1024)
            if buf:
                loader.write(buf)
                data.write(buf)
                return True # Run again
            else:
                loader.close()
                src.close()
                return False

    def __save_cover(self, data, fname):
        if os.path.exists(fname) and not qltk.ConfirmAction(None, 
            "File exists", "The file <b>%s</b> already exists."
            "\n\nOverwrite?" %util.escape(fname)).run():
            return

        f = open(fname, "w")
        f.write(data)
        f.close()
        self.destroy()

    def __get_fname(self, songs, combo):
        append = combo.get_model()[(combo.get_active(),)][0]
        dirname = songs[0]("~dirname")
        fname = os.path.join(dirname, append)
        #print "Will save to", fname
        config.set("plugins", "cover_fn", append)
        return fname

class DownloadAlbumArt(SongsMenuPlugin):
    PLUGIN_ID = "Download Album art"
    PLUGIN_NAME = _("Download Album Art")
    PLUGIN_DESC = "Downloads album covers from Amazon.com"
    PLUGIN_ICON = gtk.STOCK_FIND
    PLUGIN_VERSION = "0.25"

    def PluginPreferences(parent):
        b = gtk.Button("Visit Amazon.com")
        b.connect('clicked', lambda s: util.website('http://www.amazon.com/'))
        return b
    PluginPreferences = staticmethod(PluginPreferences)

    plugin_album = AlbumArtWindow
