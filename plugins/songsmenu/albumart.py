#Copyright 2005-2008 By:
# Eduardo Gonzalez, Niklas Janlert, Christoph Reiter, Antonio Riva
#
# Amazon API code by Mark Pilgrim.  Updated for AWS 4.0 by Kun Xi
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

# Last Modified: Wed May 21 21:16:48 EDT 2008 by <wm.eddie@gmail.com>
# - Some cleanup
# - Added to SVN
# - Bumped version number to 0.41

# Tue 2008-05-13 19:40:12 (+0200) by <wxcover@users.sourceforge.net>
# -Added walmart, darktown and buy.com cover searching.
# -Few fixes
# -Updated version number (0.25 -> 0.4)

# Mon 2008-05-05 14:54:27 (-0400)
# Updated for new Amazon API by Jeremy Cantrell <jmcantrell@gmail.com>

import os
import sys
import urllib
import re
import time
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
    from pyaws import ecs
except ImportError:
    import _ecs as ecs

class AlbumArtWindow(gtk.Window):
    def __init__(self, songs):
        gtk.Window.__init__(self)
        self.set_border_width(12)
        self.set_title("Album Art Downloader")
        self.set_default_size(850, 550)

        #TreeView stuff
        self.liststore = liststore = gtk.ListStore(object, str)
        treeview = gtk.TreeView(liststore)
        treeview.set_headers_visible(False)
        selection = treeview.get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)
        selection.connect("changed", self.__preview)

        self.url = url = gtk.Entry()
        url.set_text(songs[0]("artist") + " " + songs[0]("album"))

        urlButton = gtk.Button("Search")
        urlButton.connect("clicked", 
                          self.__start_search, url, liststore)
        url.connect("key-release-event", 
                    self.key_start_search, url, liststore)

        urlBox = gtk.HBox()
        urlBox.pack_start(url, expand=True, fill=True)
        urlBox.pack_start(urlButton, expand=False, fill=False)

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
        scrolled = gtk.ScrolledWindow()
        scrolled.add_with_viewport(frame)
        scrolled.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        vbox = gtk.VBox(spacing=5)
        vbox.pack_start(scrolled)
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

        vbox = gtk.VBox()
        vbox.pack_start(urlBox, expand=False, fill=False)
        vbox.pack_start(hpaned, expand=True, fill=True)
        self.add(vbox)

        #define search engines
        self.engines = [self.__search_amazon, self.__search_walmart,
                        self.__search_darktown, self.__search_buy]

        #max covers per site
        self.max_albums = 10

        #for progress calculation
        self.progress = 0

        #use albumartist if available
        if songs[0]("albumartist"):
            artist = songs[0]("albumartist")
        else:
            artist = songs[0]("artist")
        query = artist + " " + songs[0]("album")
        query = query

        #show search status row
        iter = self.liststore.insert(0)
        self.liststore.set(iter, 0, 
                           {"bag":None,"thumb":None,"thumb_data":None})
        self.liststore.set_value(iter, 1,
                                 "<i><b>Searching progress: 0%</b></i>")

        #start all search engines in seperate threads
        for engine in self.engines:
            thread = threading.Thread(target=self.__search,
                                      args=(query, engine, iter))
            thread.setDaemon(True)
            thread.start()

        self.show_all()

    def key_start_search(self, widget, event, entry, liststore):
        if(event.keyval == 65293): # Enter/Return key
            self.__start_search(widget, entry, liststore)


    def __start_search(self, widget, entry, liststore):
        liststore.clear()
        self.progress = 0
        entry_text = unicode(entry.get_text(), "utf-8")
        print "Search: %s\n" % entry_text

        iter = liststore.insert(0)
        liststore.set(iter, 0, {"bag":None, "thumb":None, "thumb_data":None})
        liststore.set_value(iter, 1,
                            "<i><b>Searching progress: 0%</b></i>")

        for engine in self.engines:
            thread = threading.Thread(target=self.__search, 
                                      args=(entry_text, engine, iter))
            thread.setDaemon(True)
            thread.start()

    def __destroy_cb(self, widget, *args):
        widget.destroy()
        #self.destroy()

    def __search(self, query, engine, iter):

        try:
            bags = engine(query)
            for bag in bags:
                gobject.idle_add(self.__add_bag, self.liststore, bag)
        except:
            pass

        self.progress += 1
        self.liststore.set_value(iter, 1, "<i><b>Searching progress: "
                                 +str(self.progress*100/len(self.engines))
                                 +"%</b></i>")

        if self.progress == len(self.engines):
            time.sleep(2)
            if self.liststore.iter_next(iter) == None:
                self.liststore.set_value(iter, 1,
                                         "<i><b>No albumart found</b></i>")
            else:
                self.liststore.remove(iter)

    def __search_amazon(self, uquery):
        ecs.setLicenseKey("0RKH4ZH1JCFZHMND91G2")
        #ecs.setLocale("jp")
        bags = []
        try:
            # XXX: I have no idea of all locales support utf-8, can't find
            #      any documentation on encodings.

            query = uquery.encode("utf-8", 'replace')

            # WTF: When I try this code in the interpreter It doesn't 
            #      have a .cache.  -- wm_eddie
            #bags = ecs.ItemSearch(query, 
            #                      SearchIndex='Music', 
            #                      ResponseGroup='Images,Small').cache

            for item in ecs.ItemSearch(query, 
                                       SearchIndex='Music', 
                                       ResponseGroup='Images,Small'):
                bags.append(item);
        except ecs.AWSException, msg:
            dialog = qltk.Message(gtk.MESSAGE_ERROR, None, 
                                  "Search error", msg)
            dialog.connect('response', self.__destroy_cb)
            gobject.idle_add(dialog.show)
        except UnicodeEncodeError, msg:
            dialog = qltk.Message(gtk.MESSAGE_ERROR, None, "Encoding error",
                                  msg)
            dialog.connect('response', self.__destroy_cb)
            gobject.idle_add(dialog.show)
        else:
            # Just keep the top x matches
            return bags[:self.max_albums]
        return []

    def __search_darktown(self, uquery):
        class item: pass
        bags = []

        # wm_eddie: I'm guessing this site only accepts latin-1
        query = uquery.encode("latin-1", "replace")

        #Artists @ Darkdown often miss the leading "The", better remove it
        #for better search results - also ' and . should be removed
        if query[:4] == "The ":
            query = query[4:]
        query = query.replace("'"," ")
        query = query.replace(".","")

        mainUrl = urllib.urlopen('http://www.darktown.to/search.php?'
                'action=search&what='+urllib.quote(query)+'&category=audio')
        mainData = mainUrl.read()
        mainRe = re.findall('javascript:openCentered\(\'(.*?)Front\'', 
                            mainData)

        count = 0
        for result in mainRe:
            if count >= self.max_albums: break
            count += 1

            resultUrl = urllib.urlopen('http://www.darktown.to'+result+'Front')
            resultData = resultUrl.read()

            resultImgBig = re.findall('href="(.*?)">DOWNLOAD</a>', resultData)
            resultImgSmall = re.findall(
                'src="http://img.darktown.to/thumbnail.php(.*?)"', resultData)
            resultArtist = re.findall(
                '<b><font size=4>(.*?)</font', resultData)
            resultTitle = re.findall('</font></b><br><b>(.*?)</b><br><br><b>',
                                     resultData)

            cover = item()
            cover.SmallImage = item()
            cover.LargeImage = item()
            cover.SmallImage.URL = ('http://img.darktown.to/thumbnail.php' +
                                    resultImgSmall[0])
            cover.LargeImage.URL = resultImgBig[0]
            cover.Artists = item()
            cover.Artists.Artist = resultArtist[0].decode("latin1", "replace")
            cover.ProductName = resultTitle[0].decode("latin1", "replace")

            bags.append(cover)

        return bags

    def __search_walmart(self, uquery):
        class item: pass
        bags = []

        query = uquery.encode("latin-1", "replace")

        mainUrl = urllib.urlopen('http://www.walmart.com/search/search-ng.do?'
                                 'search_constraint=4104&search_query='
                                 +urllib.quote(query)+'&ic='
                                 +str(self.max_albums)+'_0')

        mainData = mainUrl.read()

        #abort if nothing was found
        if mainData.find('0 results found for') != -1:
            return bags

        countRe = re.findall('(\d*)(\s+)results found for', mainData)

        #walmart will redirect to the specific album page
        #if the query exactly matches the product title ... so 2 ways needed
        if len(countRe):
            #abort if it returns too much shit
            if int(countRe[0][0]) > 50:
                return bags

            mainRe = re.findall(
                '<div class="ItemPic"><a href=\'.*?\'><img src='
                '\'(.*?)\' width="100" height="100" border="0" '
                'alt=\'(.*?)\'', mainData)

            artistRe = re.findall('Artist: <span class="BodySLtgry">'
                                  '(<a href=\'.*?\'>|)(.*?)(</a>|)</span>',
                                  mainData)

            for num in xrange(len(mainRe)):
                cover = item()
                cover.SmallImage = item()
                cover.LargeImage = item()
                cover.SmallImage.URL = mainRe[num][0]
                cover.LargeImage.URL = mainRe[num][0][:-11]+"500X500.jpg"
                cover.Artists = item()
                cover.Artists.Artist = artistRe[num][1]
                cover.ProductName = mainRe[num][1]

                bags.append(cover)

        else:
            mainRe = re.findall('<img src=\'(.*?)\' width="150" height="150" '
                                'border="0" alt=\'(.*?)\'', mainData)
            artistRe = re.findall(
                '<span class="BodyXSLtgry">&gt;</span>&nbsp;'
                '<a href="[^\"]*?">(.*?)</a>&nbsp;\s*', mainData)

            cover = item()
            cover.SmallImage = item()
            cover.LargeImage = item()
            cover.SmallImage.URL = mainRe[0][0][:-11]+"100X100.jpg"
            cover.LargeImage.URL = mainRe[0][0][:-11]+"500X500.jpg"
            cover.Artists = item()
            cover.Artists.Artist = artistRe[-1]
            cover.ProductName = mainRe[0][1]

            bags.append(cover)

        return bags[:self.max_albums]

    def __search_buy(self, uquery):
        class item: pass
        bags = []

        query = uquery.encode("latin-1", "replace")

        mainUrl = urllib.urlopen(
            'http://www.buy.com/retail/usersearchresults.asp?qu='
            + urllib.quote(query)+'&querytype=music&store=6&als=3&loc=109')

        mainData = mainUrl.read()

        #abort if nothing was found
        if mainData.find('We could not find an exact match for') != -1:
            return bags

        mainRe = re.findall(
            'src="([^\"]*?)" /></a></td><td width="98%" valign="top" '
            'class="list_middle"><table cellspacing="0" cellpadding="1" '
            'border="0" width="100%"><tr><td colspan="2">'
            '<span class="productDescription"><b>[0-9]+.&nbsp;</b></span>'
            '<a title="([^\"]*?)" href="([^\"]*?)" class="medBlueText"><b>', 
            mainData)

        artistRe = re.findall(
            '<span class="body"><b>Artist:</b></span>&nbsp;'
            '<a href="[^\"]*?" class="bluetext" style="padding-right:4px;">'
            '<b>(.*?)</b></a>',
            mainData)

        for num in xrange(len(mainRe)):
            cover = item()
            cover.SmallImage = item()
            cover.LargeImage = item()
            cover.SmallImage.URL = mainRe[num][0]
            cover.LargeImage.URL = mainRe[num][0].replace(
                'prod_images','large_images')
            cover.Artists = item()
            cover.Artists.Artist = artistRe[num]
            cover.ProductName = mainRe[num][1]

            bags.append(cover)

        return bags[:self.max_albums]

    def __add_bag(self, model, bag):
        # Don't show this bag if there's no large image
        if getattr(bag, 'LargeImage', None):
            # Text part
            title = util.escape(getattr(bag, "Title", ""))
            artist = (getattr(bag, "Artists", None) and
                      getattr(bag.Artists, "Artist", None) or "")
            if isinstance(artist, list):
                artist = ", ".join(artist)
            artist = util.escape(artist)
            if hasattr(bag, "ReleaseDate"):
                date = "(%s)" % util.escape(bag.ReleaseDate)
            else:
                date = ""
            markup = "<i><b>%s</b></i> %s\n%s" % (title, date, artist)

            item = {"bag": bag, "thumb": None, "thumb_data": ""}
            iter = model.append([item, markup])

            # Image part
            if getattr(bag, 'SmallImage', None):
                urlinfo = urllib.urlopen(bag.SmallImage.URL)
                sock = urlinfo.fp._sock
                sock.setblocking(0)
                data = StringIO()

                loader = gtk.gdk.PixbufLoader()
                loader.connect("closed", 
                               self.__got_thumb_cb, data, item, model, iter)

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

        if item["thumb"]: # nothing bigger if there's no thumbnail.
            if "cover" not in item:
                self.__get_cover(item, item["bag"].LargeImage.URL)
            else:
                self.image.set_from_pixbuf(item["cover"])
                self.image.show()
                self.button.set_sensitive(True)

    def __get_cover(self, item, url):
        data = StringIO()
        print url
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

        elif ((url == item["bag"].LargeImage.URL) and 
              getattr(item["bag"], 'MediumImage', None)):
            self.__get_cover(item, item["bag"].MediumImage.URL)

        elif ((url == item["bag"].LargeImage.URL) and 
              getattr(item["bag"], 'SmallImage', None)):
            self.__get_cover(item, item["bag"].SmallImage.URL)

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
    PLUGIN_DESC = "Downloads album covers from Amazon.com, " \
                  "Walmart.com, Darktown.to and Buy.com"
    PLUGIN_ICON = gtk.STOCK_FIND
    PLUGIN_VERSION = "0.41"

    def PluginPreferences(parent):
        vbox = gtk.VBox(spacing=5)
        vbox.set_border_width(5)
        bAM = gtk.Button("Visit Amazon.com")
        bAM.connect('clicked', lambda s:util.website('http://www.amazon.com/'))
        vbox.pack_start(bAM)
        bWM = gtk.Button("Visit Walmart.com")
        bWM.connect('clicked', lambda s:util.website('http://www.walmart.com/'))
        vbox.pack_start(bWM)
        bDT = gtk.Button("Visit Darktown.to")
        bDT.connect('clicked', lambda s:util.website('http://www.darktown.to/'))
        vbox.pack_start(bDT)
        bBU = gtk.Button("Visit Buy.com")
        bBU.connect('clicked', lambda s:util.website('http://www.buy.com/'))
        vbox.pack_start(bBU)
        return vbox

    PluginPreferences = staticmethod(PluginPreferences)

    plugin_album = AlbumArtWindow
