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
        print QueryParser(QueryLexer(textbox.get_text())).Query()

class Widgets(object):
    def __init__(self, file):
        self.widgets = gtk.glade.XML("quodlibet.glade")
        self.widgets.signal_autoconnect(GladeHandlers.__dict__)

    def __getitem__(self, key):
        return self.widgets.get_widget(key)

HEADERS = ["artist", "title", "album"]

def main():
    widgets = Widgets("quodlibet.glade")
    sl = widgets["songlist"]
    store = gtk.ListStore(*([gobject.TYPE_STRING] * len(HEADERS)))

    for i, t in enumerate(HEADERS):
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(t.title(), renderer, text=i)
        sl.append_column(column)

    library.load(sys.argv[1:])
    print library.songs
    for song in library.songs:
        store.append([song.get(i, "") for i in HEADERS])
    sl.set_model(store)
    print store[0]
    gtk.main()

if __name__ == "__main__": main()
