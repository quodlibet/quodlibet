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
            for song in library.load(chooser.get_filenames()):
                widgets.songs.append([song] +
                                     [song.get(i, "") for i in HEADERS])
        chooser.destroy()
        GladeHandlers.text_parse(GladeHandlers())

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

def main():
    sl = widgets["songlist"]
    widgets.songs = gtk.ListStore(*([object] + [str] * len(HEADERS)))
    widgets.filter = widgets.songs.filter_new()
    widgets.filter.set_visible_func(lambda m, i, q: bool(q[0](m[i][0])),
                                    CURRENT_FILTER)
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
