#!/usr/bin/env python

# Copyright 2004 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import pygtk
pygtk.require('2.0')
import gtk
import gtk.glade
from library import library
import player
import threading
import gc
import os
import util; from util import escape
import signal
import config

class GTKSongInfoWrapper(object):
    def __init__(self):
        self.image = widgets["albumcover"]
        self.vbar = widgets["vseparator2"]
        self.text = widgets["currentsong"]
        self.pos = widgets["song_pos"]
        self.timer = widgets["song_timer"]
        self.button = widgets["play_button"]
        self.playing = gtk.gdk.pixbuf_new_from_file("pause.png")
        self.paused = gtk.gdk.pixbuf_new_from_file("play.png")

        self._time = (0, 1)
        gtk.timeout_add(300, self._update_time)

    def set_paused(self, paused):
        gtk.idle_add(self._update_paused, paused)

    def _update_paused(self, paused):
        img = self.button.get_icon_widget()
        if paused: img.set_from_pixbuf(self.paused)
        else: img.set_from_pixbuf(self.playing)

    def set_song(self, song, player):
        gtk.idle_add(self._update_song, song, player)

    def set_time(self, cur, end):
        self._time = (cur, end)

    def _update_song(self, song, player):
        if song:
            self.pos.set_range(0, player.length)
            self.pos.set_value(0)

            cover = song.find_cover()
            if cover:
                pixbuf = gtk.gdk.pixbuf_new_from_file(cover)
                pixbuf = pixbuf.scale_simple(100, 100, gtk.gdk.INTERP_BILINEAR)
                self.image.set_from_pixbuf(pixbuf)
                self.image.show()
                self.vbar.show()
            else:
                self.image.hide()
                self.vbar.hide()

            self.text.set_markup(song.to_markup())
        else:
            self.image.set_from_stock(gtk.STOCK_CDROM, gtk.ICON_SIZE_BUTTON)
            self.pos.set_range(0, 1)
            self.pos.set_value(0)
            self._time = (0, 1)
            self.text.set_markup("<span size='xx-large'>Not playing</span>")
        last_song = CURRENT_SONG[0]
        CURRENT_SONG[0] = song
        def update_if_last_or_current(model, path, iter, changed):
            if model[iter][0] in changed: model.row_changed(path, iter)
        widgets.songs.foreach(update_if_last_or_current, (last_song, song))
        return False

    def _update_time(self):
        cur, end = self._time
        self.pos.set_value(cur)
        self.timer.set_text("%d:%02d/%d:%02d" %
                            (cur / 60000, (cur % 60000) / 1000,
                             end / 60000, (end % 60000) / 1000))
        return True

def make_chooser(title):
    chooser = gtk.FileChooserDialog(
        title = "Add Music",
        action = gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
        buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                   gtk.STOCK_OPEN, gtk.RESPONSE_OK))
    chooser.set_select_multiple(True)
    resp = chooser.run()
    fns = chooser.get_filenames()
    chooser.destroy()
    return resp, fns

class Widgets(object):
    def __init__(self, file):
        self.widgets = gtk.glade.XML("quodlibet.glade")
        self.widgets.signal_autoconnect(GladeHandlers.__dict__)

    def __getitem__(self, key):
        return self.widgets.get_widget(key)

class GladeHandlers(object):
    def gtk_main_quit(*args): gtk.main_quit()

    def play_pause(button):
        player.playlist.paused ^= True

    def next_song(*args):
        player.playlist.next()

    def previous_song(*args):
        player.playlist.previous()

    def toggle_repeat(button):
        player.playlist.repeat = button.get_active()

    def toggle_shuffle(button):
        player.playlist.shuffle = button.get_active()

    def seek_slider(slider, v):
        gtk.idle_add(player.playlist.seek, v)

    def open_prefs(*args):
        widgets["prefs_window"].set_transient_for(widgets["main_window"])
        widgets["cover_t"].set_active(config.state("cover"))
        widgets["color_t"].set_active(config.state("color"))
        widgets["scan_opt"].set_text(config.get("settings", "scan"))
        widgets["prefs_window"].show()

    def change_scan(*args):
        config.set("settings", "scan", widgets["scan_opt"].get_text())

    def select_scan(*args):
        resp, fns = make_chooser("Select Directories")
        if resp == gtk.RESPONSE_OK:
            widgets["scan_opt"].set_text(":".join(fns))

    def prefs_closed(*args):
        widgets["prefs_window"].hide()
        return True

    def select_song(tree, indices, col):
        iter = widgets.songs.get_iter(indices)
        song = widgets.songs.get_value(iter, 0)
        player.playlist.go_to(song)
        player.playlist.paused = False

    def open_chooser(*args):
        resp, fns = make_chooser("Add Music")
        if resp == gtk.RESPONSE_OK:
            library.scan(fns)
            songs = filter(CURRENT_FILTER[0], library.values())
            player.playlist.set_playlist(songs)
            refresh_songlist()
            gc.collect()

    def update_volume(slider):
        player.device.volume = int(slider.get_value())

    def text_parse(*args):
        from parser import QueryParser, QueryLexer
        text = widgets["query"].get_text().decode("utf-8")
        if text.strip() == "":
            CURRENT_FILTER[0] = FILTER_ALL
            songs = filter(CURRENT_FILTER[0], library.values())
            player.playlist.set_playlist(songs)
            refresh_songlist()
        else:
            if "=" not in text and "/" not in text:
                parts = ["* = /" + p + "/" for p in text.split()]
                text = "&(" + ",".join(parts) + ")"
                q = QueryParser(QueryLexer(text)).Query()
                widgets["query"].set_text(text)

            try: q = QueryParser(QueryLexer(text)).Query()
            except: pass
            else:
                CURRENT_FILTER[0] = q.search
                set_entry_color(widgets["query"], "black")
                songs = filter(CURRENT_FILTER[0], library.values())
                player.playlist.set_playlist(songs)
                refresh_songlist()

    def test_filter(*args):
        from parser import QueryParser, QueryLexer
        textbox = widgets["query"]
        text = textbox.get_text()
        if "=" not in text and "/" not in text:
            gtk.idle_add(set_entry_color, textbox, "blue")
        else:
            try:
                QueryParser(QueryLexer(text)).Query()
            except:
                gtk.idle_add(set_entry_color, textbox, "red")
            else:
                gtk.idle_add(set_entry_color, textbox, "dark green")

def set_sort_by(header, i):
    s = header.get_sort_order()
    if not header.get_sort_indicator() or s == gtk.SORT_DESCENDING:
        s = gtk.SORT_ASCENDING
    else: s = gtk.SORT_DESCENDING
    for h in widgets["songlist"].get_columns():
        h.set_sort_indicator(False)
    header.set_sort_indicator(True)
    header.set_sort_order(s)
    player.playlist.sort_by(HEADERS[i[0]], s == gtk.SORT_DESCENDING)
    refresh_songlist()

def refresh_songlist():
    widgets.songs.clear()
    i = 0
    statusbar = widgets["statusbar"]
    for song in player.playlist:
         widgets.songs.append([song])
         i += 1
    j = statusbar.get_context_id("playlist")
    statusbar.push(j, "%d song%s found." % (i, (i != 1 and "s" or "")))

widgets = Widgets("quodlibet.glade")

HEADERS = ["=#", "title", "album", "artist"]
HEADERS_FILTER = { "=#": "Track", "tracknumber": "Track" }

FILTER_ALL = lambda x: True
CURRENT_FILTER = [ FILTER_ALL ]
CURRENT_SONG = [ None ]

def list_transform(model, iter, col):
    citer = model.convert_iter_to_child_iter(iter)
    cmodel = model.get_model()
    song = cmodel.get_value(citer, 0)
    try: return song.get(HEADERS[col], "")
    except IndexError: return song is CURRENT_SONG[0] and 700 or 400

def set_entry_color(entry, color):
    layout = entry.get_layout()
    text = layout.get_text()
    markup = '<span foreground="%s">%s</span>' % (color, escape(text))
    layout.set_markup(markup)

def set_column_headers(sl):
    widgets.filter = widgets.songs.filter_new()
    widgets.filter.set_modify_func([str]*len(HEADERS) + [int], list_transform)
    for c in sl.get_columns(): sl.remove_column(c)
    for i, t in enumerate(HEADERS):
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(HEADERS_FILTER.get(t, t).title(),
                                    renderer, text = i, weight = len(HEADERS))
        column.set_resizable(True)
        column.set_clickable(True)
        column.set_sort_indicator(False)
        column.connect('clicked', set_sort_by, (i,))
        sl.append_column(column)
    sl.set_model(widgets.filter)

def main():
    sl = widgets["songlist"]
    widgets.songs = gtk.ListStore(object)
    widgets["volume"].set_value(player.device.volume)
    config_fn = os.path.join(os.environ["HOME"], ".quodlibet", "config")
    config.init(config_fn)
    cache_fn = os.path.join(os.environ["HOME"], ".quodlibet", "songs")
    library.load(cache_fn)
    if config.get("settings", "scan"):
        library.scan(config.get("settings", "scan").split(":"))
    player.playlist.set_playlist(library.values())
    player.playlist.sort_by(HEADERS[0])
    widgets.songs.clear()
    i = 0
    for song in player.playlist:
         widgets.songs.append([song])
         i += 1
    set_column_headers(sl)
    statusbar = widgets["statusbar"]
    j = statusbar.get_context_id("playlist")
    statusbar.push(j, "%d song%s found." % (i, (i != 1 and "s" or "")))
    
    print "Done loading songs."
    gtk.threads_init()
    t = threading.Thread(target = player.playlist.play,
                         args = (GTKSongInfoWrapper(),))
    gc.collect()
    signal.signal (signal.SIGINT, signal.SIG_DFL)
    t.start()
    widgets["main_window"].show()
    try: gtk.main()
    except: gtk.main_quit()
    player.playlist.quitting()
    t.join()
    util.mkdir(os.path.join(os.environ["HOME"], ".quodlibet"))
    library.save(cache_fn)
    config.write(file(config_fn, "w"))

if __name__ == "__main__": main()
