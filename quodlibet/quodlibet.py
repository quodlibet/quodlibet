#!/usr/bin/env python

import pygtk
pygtk.require('2.0')
import gtk
import gtk.glade
import gobject
import sys
import parser
import library
import player
import thread
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

    def play_pause(*args):
        player.paused ^= True

    def select_song(tree, indices, col):
        iter = widgets.sorted.get_iter(indices)
        iter = widgets.sorted.convert_iter_to_child_iter(None, iter)
        iter = widgets.filter.convert_iter_to_child_iter(iter)
        song = widgets.songs.get_value(iter, 0)
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

        cover = song.get("cover", None)
        if cover and os.path.exists(cover):
            pixbuf = gtk.gdk.pixbuf_new_from_file(cover)
            scaled_buf = pixbuf.scale_simple(100, 100,
                                             gtk.gdk.INTERP_BILINEAR)
            widgets["albumcover"].set_from_pixbuf(scaled_buf)
        else:
            widgets["albumcover"].set_from_stock(gtk.STOCK_CDROM,
                                                 gtk.ICON_SIZE_BUTTON)
        label.set_markup(text)
        player.set_playlist([song])
        player.paused = False

    def open_chooser(*args):
        chooser = gtk.FileChooserDialog(
            title = "Add Music",
            action = gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
            buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                       gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        chooser.set_select_multiple(True)
        resp = chooser.run()
        if resp == gtk.RESPONSE_OK:
            library.load(chooser.get_filenames())
            songs = filter(CURRENT_FILTER[0], library.library.values())
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
        player.queue.append(('seek', (v,)))

    def update_volume(slider):
        player.queue.append(('volume', (int(slider.get_value()),)))

    def text_parse(*args):
        from parser import QueryParser, QueryLexer
        text = widgets["query"].get_text()
        if text.strip() == "":
            CURRENT_FILTER[0] = FILTER_ALL
            songs = filter(CURRENT_FILTER[0], library.library.values())
            set_songs(songs)
        else:
            try:
                q = QueryParser(QueryLexer(text)).Query()
            except: pass
            else:
                CURRENT_FILTER[0] = q.search
                set_entry_color(widgets["query"], "black")
                songs = filter(CURRENT_FILTER[0], library.library.values())
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
    player.set_playlist(songs)

widgets = Widgets("quodlibet.glade")

HEADERS = ["artist", "title", "album"]

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
    widgets.filter.set_visible_func(lambda m, i: bool(m[i][0]))
    widgets.filter.set_modify_func([str]*len(HEADERS), list_transform)
    widgets.sorted = gtk.TreeModelSort(widgets.filter)
    vol = widgets["volume"]
    vol.set_value(player.get_volume())
    for i, t in enumerate(HEADERS):
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(t.title(), renderer, text=i)
        column.set_resizable(True)
        column.set_sort_column_id(i)
        sl.append_column(column)

    set_songs(library.load_cache())
    print "Done loading songs."
    sl.set_model(widgets.sorted)
    widgets.sorted.set_sort_column_id(0, gtk.SORT_ASCENDING)
    gc.collect()
    player.paused = True
    gtk.timeout_add(500, update_timer, ())
    gtk.threads_init()
    thread.start_new_thread(player.play, (widgets["currentsong"],))
    gtk.main()
    library.save_cache([row[0] for row in widgets.songs])

if __name__ == "__main__": main()
