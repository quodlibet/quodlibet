#!/usr/bin/env python

import pygtk
pygtk.require('2.0')
import gtk
import gtk.glade
import gobject
import sys
import parser
import library
import gc
import os

def escape(str):
    return str.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

class Widgets(object):
    def __init__(self, file):
        self.widgets = gtk.glade.XML("quodlibet.glade")
        self.widgets.signal_autoconnect(GladeHandlers.__dict__)

    def __getitem__(self, key):
        return self.widgets.get_widget(key)

class GladeHandlers(object):
    def gtk_main_quit(*args): gtk.main_quit()

    def select_song(tree, indices, col):
        model = widgets.sorted
        song = model[model.get_iter(indices)][0]
        title = ", ".join(song.get("title", "Unknown").split("\n"))

        text = u'<span weight="bold" size="x-large">%s</span>' % escape(title)
        if "version" in song:
            text += u"\n         <small><b>%s</b></small>" % escape(
                song["version"])

        artist = ", ".join(song.get("artist", "Unknown").split("\n"))
        text += u"\n      <small>by %s</small>" % escape(artist)
        if "album" in song:
            album = u"\n   <b>%s</b>" % escape(song["album"])
            if "tracknumber" in song:
                album += u" - Track %s" % escape(song["tracknumber"])
            text += album
        label = widgets["currentsong"]

        cover = os.path.split(song["filename"])[0]
        cover = os.path.join(cover, "cover.jpg")
        if os.path.exists(cover):
            pixbuf = gtk.gdk.pixbuf_new_from_file(cover)
            scaled_buf = pixbuf.scale_simple(100, 100, gtk.gdk.INTERP_BILINEAR)
            widgets["albumcover"].set_from_pixbuf(scaled_buf)
        else:
            widgets["albumcover"].set_from_stock(gtk.STOCK_CDROM,
                                                       gtk.ICON_SIZE_BUTTON)
        label.set_markup(text)

    def open_chooser(*args):
        chooser = gtk.FileChooserDialog(
            title = "Add Music",
            action = gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
            buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                       gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        chooser.set_select_multiple(True)
        resp = chooser.run()
        if resp == gtk.RESPONSE_OK:
            CURRENT_FILTER.insert(0, FILTER_ALL)
            for song in library.load(chooser.get_filenames()):
                widgets.songs.append([song] +
                                     [song.get(i, "") for i in HEADERS])
            CURRENT_FILTER.pop(0)
        chooser.destroy()
        widgets.filter.refilter()

    def text_parse(*args):
        from parser import QueryParser, QueryLexer
        text = widgets["query"].get_text()
        if text.strip() == "":
            CURRENT_FILTER[0] = FILTER_ALL
            widgets.filter.refilter()
        else:
            try:
                q = QueryParser(QueryLexer(text)).Query()
            except: pass
            else:
                CURRENT_FILTER[0] = q.search
                widgets.filter.refilter()

widgets = Widgets("quodlibet.glade")

HEADERS = ["artist", "title", "album"]

FILTER_ALL = lambda x: True
CURRENT_FILTER = [ FILTER_ALL ]

def list_filter(m, i, q):
    return bool(q[0](m[i][0]))

def main():
    sl = widgets["songlist"]
    widgets.songs = gtk.ListStore(*([object] + [str] * len(HEADERS)))
    widgets.filter = widgets.songs.filter_new()
    widgets.filter.set_visible_func(list_filter, CURRENT_FILTER)
    widgets.sorted = gtk.TreeModelSort(widgets.filter)

    for i, t in enumerate(HEADERS):
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(t.title(), renderer, text=i+1)
        column.set_resizable(True)
        column.set_sort_column_id(i+1)
        sl.append_column(column)

    for song in library.load(sys.argv[1:]):
        widgets.songs.append([song] + [song.get(i, "") for i in HEADERS])
    sl.set_model(widgets.sorted)
    sl.set_reorderable(True)
    widgets.sorted.set_sort_column_id(1, gtk.SORT_ASCENDING)
    gc.collect()
    gtk.main()

if __name__ == "__main__": main()
