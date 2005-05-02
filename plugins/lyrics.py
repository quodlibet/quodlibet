# Copyright 2005 Eduardo Gonzalez
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

# TODO: x Make the urlopen() run in the background
#       * Properly escape unicode in the url
#       * Use SAX instead of minidom to parse the results
#       x Use qltk for the dialogs
#       * Make the GUI better: (add the buttons on the top, 
#         use better names, etc.)
#       * Give the user some way to choose what gets displayed when an exact
#         match isn't found
#       * Add support for more lyrics databases

import os
import gtk, gobject
import urllib
from xml.dom import minidom
import threading
import qltk
import util

PLUGIN_NAME = "Show the lyrics"
PLUGIN_DESC = "Search for and save the lyrics of songs, using lyrc.com.ar."
PLUGIN_ICON = gtk.STOCK_EDIT #For now
PLUGIN_VERSION = "0.11"

class LyricWindow(gtk.Window):
    def __init__(self, song):
        gtk.Window.__init__(self)
        self.set_border_width(12)
        self.set_title(song.comma("title") + " - Lyrics")

        icon_theme = gtk.icon_theme_get_default()
        self.set_icon(icon_theme.load_icon(
            'quodlibet-icon', 64, gtk.ICON_LOOKUP_USE_BUILTIN))

        vbox = gtk.VBox(spacing=12)
        view = gtk.TextView()
        sw = gtk.ScrolledWindow()
        sw.add(view)
        refresh = gtk.Button(stock=gtk.STOCK_REFRESH)
        save = gtk.Button(stock=gtk.STOCK_SAVE)
        delete = gtk.Button(stock=gtk.STOCK_DELETE)
        view.set_wrap_mode(gtk.WRAP_WORD)
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)

        lyricname = self.__lyricname(song)

        buffer = view.get_buffer()
        refresh.connect('clicked', self.__refresh, buffer, song)
        save.connect(
            'clicked', self.__save, lyricname, buffer, delete)
        delete.connect('clicked', self.__delete, lyricname, save)

        sw.set_shadow_type(gtk.SHADOW_IN)
        vbox.pack_start(sw, expand=True)
        bbox = gtk.HButtonBox()
        bbox.pack_start(save)
        bbox.pack_start(delete)
        bbox.pack_start(refresh)
        vbox.pack_start(bbox, expand=False)

        save.set_sensitive(False)
        if os.path.exists(lyricname):
            buffer.set_text(file(lyricname).read())
        else:
            buffer.set_text("Searching for lyrics...\n\n")
            delete.set_sensitive(False)
            refresh.set_sensitive(False)
            thread = threading.Thread(
                target=self.__search, args=(song, buffer, refresh))
            thread.setDaemon(True)
            thread.start()
        buffer.connect_object('changed', save.set_sensitive, True)

        self.add(vbox)
        self.set_default_size(350, 250)
        self.show_all()

    def __refresh(self, refresh, buffer, song):
        buffer.set_text("Searching for lyrics...\n\n")
        refresh.set_sensitive(False)
        thread = threading.Thread(
            target=self.__search, args=(song, buffer, refresh))
        thread.setDaemon(True)
        thread.start()

    def __search(self, song, buffer, refresh):
        artist = song.comma("artist")
        title = song.comma("title")
        sock = urllib.urlopen(
            "http://lyrc.com.ar/xsearch.php?songname=%s&artist=%s&act=1"%(
            urllib.quote(title.encode('utf-8')),
            urllib.quote(artist.encode('utf-8'))))

        try: xmldoc = minidom.parse(sock).documentElement
        except:
            gobject.idle_add(buffer.set_text, "Server did not respond.")
            gobject.idle_add(refresh.set_sensitive, True)
            return

        sock.close()

        result_nodes = xmldoc.getElementsByTagName('result')
        if result_nodes.length > 0:
            name = result_nodes[0].childNodes[1].childNodes[0].nodeValue
            group = result_nodes[0].childNodes[2].childNodes[0].nodeValue
            lyrics = result_nodes[0].childNodes[3].childNodes[0].nodeValue

            if name != title:
                text = ("Displaying the closest match found:\n\n" +
                        group + "\n" + name + "\n\n" + lyrics +
                        "\n\nLyrics provided by lyrc.com.ar.")
            elif name == title:
                text = (group + "\n" + name + "\n\n" + lyrics +
                        "\n\nLyrics provided by lyrc.com.ar.")
            else:  text = "No lyrics found.\n"
        else: text = "Server did not respond.\n"

        gobject.idle_add(buffer.set_text, text)
        gobject.idle_add(refresh.set_sensitive, True)

        xmldoc.unlink()

    def __lyricname(self, song):
        return util.fsencode(os.path.join(
            os.path.expanduser("~/.lyrics"),
            song.comma("artist").replace('/', ''),
            song.comma("album").replace('/', ''),
            song.comma("title").replace('/', '') + '.lyric'))

    def __save(self, save, lyricname, buffer, delete):
        if os.path.exists(lyricname):
            if not qltk.ConfirmAction(
                self, "Overwrite lyric file?",
                "<b>%s</b> already exists. Overwrite it?" %(
                util.escape(lyricname))).run():
                return

        try: os.makedirs(os.path.dirname(lyricname))
        except EnvironmentError, err: pass

        try: f = file(lyricname, "w")
        except EnvironmentError, err: print err
        else:
            start, end = buffer.get_bounds()
            f.write(buffer.get_text(start, end))
            f.close()
        delete.set_sensitive(True)
        save.set_sensitive(False)

    def __delete(self, delete, lyricname, save):
        try: os.unlink(lyricname)
        except EnvironmentError: pass
        valid = 3 # .lyrics, artist, album
        while valid:
            lyricname = os.path.dirname(lyricname)
            try: os.rmdir(lyricname)
            except EnvironmentError: valid = False
            else: valid -= 1
        delete.set_sensitive(False)
        save.set_sensitive(True)

plugin_song = LyricWindow
