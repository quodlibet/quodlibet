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

class GladeHandlers(object):
    def gtk_main_quit(*args): gtk.main_quit()

    def select_song(tree, indices, col):
        song = library.current[indices[0]]
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

    def text_parse(textbox):
        from parser import QueryParser, QueryLexer
        try:
            textbox = widgets["query"]
            q = QueryParser(QueryLexer(textbox.get_text())).Query()
            library.current = filter(q.search, library.songs)
            store = widgets.songs
            store.clear()
            for song in library.current:
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
    library.current = library.songs
    for song in library.current:
        widgets.songs.append([song.get(i, "") for i in HEADERS])
    sl.set_model(widgets.songs)
    gc.collect()
    gtk.main()

if __name__ == "__main__": main()
