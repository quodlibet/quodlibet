#!/usr/bin/env python

import pygtk
pygtk.require('2.0')
import gtk
import gtk.glade
import gobject
import sys
import parser
import library

class GladeHandlers(object):
    def gtk_main_quit(*args): gtk.main_quit()

    def text_parse(textbox):
        from parser import QueryParser, QueryLexer
        try:
            q = QueryParser(QueryLexer(textbox.get_text())).Query()
            songs = filter(q.search, library.songs)
            store = widgets.songs
            store.clear()
            for song in songs:
                store.append([song.get(i, "") for i in HEADERS])
        except:
            pass

class Widgets(object):
    def __init__(self, file):
        self.widgets = gtk.glade.XML("quodlibet.glade")
        self.widgets.signal_autoconnect(GladeHandlers.__dict__)

    def __getitem__(self, key):
        return self.widgets.get_widget(key)

HEADERS = ["artist", "title", "album"]

widgets = Widgets("quodlibet.glade")

def main():
    sl = widgets["songlist"]
    widgets.songs = gtk.ListStore(*([gobject.TYPE_STRING] * len(HEADERS)))

    for i, t in enumerate(HEADERS):
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(t.title(), renderer, text=i)
        sl.append_column(column)

    library.load(sys.argv[1:])
    print library.songs
    for song in library.songs:
        widgets.songs.append([song.get(i, "") for i in HEADERS])
    sl.set_model(widgets.songs)
    gtk.main()

if __name__ == "__main__": main()
