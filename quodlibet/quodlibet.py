#!/usr/bin/env python

import pygtk
pygtk.require('2.0')
import gtk
import gtk.glade
import gobject
import sys
import parser
from library import library
import player
import thread
import gc
import os
import util; from util import escape

class GTKImageWrapper(object):
    def __init__(self, widget, x = 100, y = 100):
        self.widget = widget
        self.x = x
        self.y = y

    def set_image(self, filename):
        if filename:
            pixbuf = gtk.gdk.pixbuf_new_from_file(filename)
            scaled_buf = pixbuf.scale_simple(self.x, self.y,
                                             gtk.gdk.INTERP_BILINEAR)
            self.widget.set_from_pixbuf(scaled_buf)
        else:
            self.widget.set_from_stock(gtk.STOCK_CDROM,
                                       gtk.ICON_SIZE_BUTTON)
class Widgets(object):
    def __init__(self, file):
        self.widgets = gtk.glade.XML("quodlibet.glade")
        self.widgets.signal_autoconnect(GladeHandlers.__dict__)

    def __getitem__(self, key):
        return self.widgets.get_widget(key)

class GladeHandlers(object):
    def gtk_main_quit(*args): gtk.main_quit()

    def play_pause(*args):
        player.playlist.paused ^= True

    def next_song(*args):
        player.playlist.next()

    def previous_song(*args):
        player.playlist.previous()

    def toggle_repeat(button):
        player.playlist.repeat = button.get_active()

    def select_song(tree, indices, col):
        iter = widgets.songs.get_iter(indices)
        #iter = widgets.songs.convert_iter_to_child_iter(None, iter)
        #iter = widgets.filter.convert_iter_to_child_iter(iter)
        song = widgets.songs.get_value(iter, 0)
        player.playlist.go_to(song)
        player.playlist.paused = False

    def open_chooser(*args):
        chooser = gtk.FileChooserDialog(
            title = "Add Music",
            action = gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
            buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                       gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        chooser.set_select_multiple(True)
        resp = chooser.run()
        if resp == gtk.RESPONSE_OK:
            library.scan(chooser.get_filenames())
            songs = filter(CURRENT_FILTER[0], library.values())
            set_songs(songs)
        chooser.destroy()

    def update_pos_text(*args):
        timer = widgets["song_timer"]
        cur, end = player.times
        cur = args[0].get_value()
        if cur:
            timer.set_text("%d:%02d/%d:%02d" %
                           (cur / 60000, (cur % 60000) / 1000,
                            end / 60000, (end % 60000) / 1000))
        else:
            timer.set_text("0:00/0:00")

    def moved_seek_slider(*args):
        v = min(player.times[1], max(0, args[0].get_value()))
        player.playlist.seek(v)

    def update_volume(slider):
        player.device.volume = int(slider.get_value())

    def text_parse(*args):
        from parser import QueryParser, QueryLexer
        text = widgets["query"].get_text()
        if text.strip() == "":
            CURRENT_FILTER[0] = FILTER_ALL
            songs = filter(CURRENT_FILTER[0], library.values())
            set_songs(songs)
        else:
            try:
                q = QueryParser(QueryLexer(text)).Query()
            except: pass
            else:
                CURRENT_FILTER[0] = q.search
                set_entry_color(widgets["query"], "black")
                songs = filter(CURRENT_FILTER[0], library.values())
                set_songs(songs)

    def test_filter(*args):
        from parser import QueryParser, QueryLexer
        textbox = widgets["query"]
        text = textbox.get_text()
        try:
            QueryParser(QueryLexer(text)).Query()
        except:
            gtk.idle_add(set_entry_color, textbox, "red")
        else:
            gtk.idle_add(set_entry_color, textbox, "dark green")

def set_songs(songs):
    widgets.songs.clear()
    for song in songs: widgets.songs.append([song])
    player.playlist.set_playlist(songs)

def sort_songs(a, b):
    h = MAINHEADER[0]
    return (cmp(a.get(h), b.get(h)) or
            cmp(a.get("artist"), b.get("artist")) or
            cmp(a.get("album"), b.get("album")) or
            cmp(a.get("tracknumber"), b.get("tracknumber")) or
            cmp(a.get("title"), b.get("title")))

def set_sort_by(header, i):
    s = header.get_sort_order()
    if s == gtk.SORT_ASCENDING: s = gtk.SORT_DESCENDING
    else: s = gtk.SORT_ASCENDING
    header.set_sort_order(s)
    print header, i

widgets = Widgets("quodlibet.glade")

HEADERS = ["artist", "title", "album"]
MAINHEADER = ["artist"]

FILTER_ALL = lambda x: True
CURRENT_FILTER = [ FILTER_ALL ]

def list_transform(model, iter, col):
    citer = model.convert_iter_to_child_iter(iter)
    cmodel = model.get_model()
    song = cmodel.get_value(citer, 0)
    return song.get(HEADERS[col], "")

def set_entry_color(entry, color):
    layout = entry.get_layout()
    text = layout.get_text()
    markup = '<span foreground="%s">%s</span>' % (color, escape(text))
    layout.set_markup(markup)

def update_timer(*args):
    pos = widgets["song_pos"]
    cur, end = player.times
    if end:
        pos.set_range(0, end)
        pos.set_value(cur)
    else:
        pos.set_value(0)
    return True

def main():
    sl = widgets["songlist"]
    widgets.songs = gtk.ListStore(object)
    widgets.filter = widgets.songs.filter_new()
    widgets.filter.set_modify_func([str]*len(HEADERS), list_transform)
    vol = widgets["volume"]
    vol.set_value(player.device.volume)
    for i, t in enumerate(HEADERS):
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(t.title(), renderer, text=i)
        column.set_resizable(True)
        column.set_clickable(True)
        column.set_sort_indicator(True)
        column.connect('clicked', set_sort_by, (i,))
        sl.append_column(column)

    cache_fn = os.path.join(os.environ["HOME"], ".quodlibet", "songs")
    library.load(cache_fn)
    set_songs(library.values())
    print "Done loading songs."
    sl.set_model(widgets.filter)
    #widgets.sorted.set_sort_column_id(0, gtk.SORT_ASCENDING)
    gc.collect()
    gtk.timeout_add(100, update_timer, ())
    gtk.threads_init()
    thread.start_new_thread(player.playlist.play,
                            (widgets["currentsong"],
                             GTKImageWrapper(widgets["albumcover"])))
    gtk.main()
    util.mkdir(os.path.join(os.environ["HOME"], ".quodlibet"))
    library.save(cache_fn)

if __name__ == "__main__": main()
