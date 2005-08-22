#Copyright 2005 Eduardo Gonzalez
#Amazon API code by Mark Pilgrim
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import re
import gtk, gobject
import util
import qltk
import config
import urllib
import tempfile

try:
    import amazon
except ImportError:
    qltk.ErrorMessage(None,
                      "Module not found",
                      "<b>Unable to load amazon.py</b>\n" +
                      "Please make sure amazon.py is in your plugins folder.  " +
                      "A compatible version can be found in the Quod Libet " +
                      "Subversion repository.").run()

PLUGIN_NAME = "Download Album art"
PLUGIN_DESC = "Downloads album covers from Amazon.com"
PLUGIN_ICON = gtk.STOCK_FIND
PLUGIN_VERSION = "0.13"

class AlbumArtWindow(gtk.Window):
    def __init__(self, songs):
        gtk.Window.__init__(self)
        self.set_border_width(12)
        self.songlist = []
        self.set_title("AlbumArt")
        self.set_size_request(200, 200)
        
        icon_theme = gtk.icon_theme_get_default()
        self.set_icon(icon_theme.load_icon(
            'quodlibet-icon', 64, gtk.ICON_LOOKUP_USE_BUILTIN))

        hbox = gtk.HBox(spacing=12)

        #TreeView stuff
        liststore = gtk.ListStore(gtk.gdk.Pixbuf, str)
        treeview = gtk.TreeView(liststore)
        treeview.set_headers_visible(False)

        tvcol1 = gtk.TreeViewColumn("Pixbuf")
        tvcol2 = gtk.TreeViewColumn("Info")
        cellp = gtk.CellRendererPixbuf()
        cellt = gtk.CellRendererText()
        tvcol1.pack_start(cellp)
        tvcol2.pack_start(cellt)
        treeview.append_column(tvcol1)
        treeview.append_column(tvcol2)

        self.__search(liststore, songs)
        
        hbox.pack_start(treeview)
        self.add(hbox)
        
    def __search(self, model, songs):
        artist = songs[0]('artist')
        album = songs[0]('album')
        fn = songs[0]('~filename')
        fn = os.path.join(os.path.dirname(fn), ".folder.jpg")
        print "Will save to %s" % fn

        amazon.setLicense("0RKH4ZH1JCFZHMND91G2")
        bags = amazon.searchByKeyword(artist+'+'+album,
                                      type="lite", product_line="music")
        for bag in bags: pass
        #bags[0].ImageUrlLarge

        sock = urllib.urlopen(bags[0].ImageUrlSmall)
        loader = gtk.gdk.PixbufLoader()
        print "Connect"
        loader.connect("area-prepared", self.__add_image, model, album)
        print "loader.write"
        loader.write(sock.read())
        sock.close()
        
    def __add_image(self, loader, model, text):
        print "add image"
        model.append([loader.get_pixbuf(), text])
        print "loader.close()"
        loader.close()
        self.show_all()
        
    def PluginPreferences(parent):
        b = gtk.Button("Visit Amazon.com")
        b.connect('clicked', lambda s: util.website('http://www.amazon.com/'))
        return b

plugin_album = AlbumArtWindow
