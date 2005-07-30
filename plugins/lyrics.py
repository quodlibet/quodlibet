# Copyright 2005 Eduardo Gonzalez
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

# TODO: * Use different lyrics sites for different languages

import os
import gtk, gobject
import urllib
from xml.dom import minidom
import threading
import qltk
import util

PLUGIN_NAME = "Show the lyrics"
PLUGIN_DESC = "Search for and save the lyrics of songs, using leolyrics.com."
PLUGIN_ICON = gtk.STOCK_EDIT #For now
PLUGIN_VERSION = "0.12"

class LyricWindow(gtk.Window):
    
    def __init__(self, song):
        gtk.Window.__init__(self)
        self.set_border_width(12)
        self.songlist = []
        self.set_title(song.comma("title") + " - " +
		       song.comma("artist") + " - Lyrics")

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
        add = gtk.Button(stock=gtk.STOCK_ADD)
        view.set_wrap_mode(gtk.WRAP_WORD)
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)

        lyricname = self.__lyricname(song)
        buffer = view.get_buffer()

        refresh.connect('clicked', self.__refresh, add, buffer, song)
        save.connect('clicked', self.__save, lyricname, buffer, delete)
        delete.connect('clicked', self.__delete, lyricname, save)
        add.connect('clicked', self.__add, song)

        sw.set_shadow_type(gtk.SHADOW_IN)
        vbox.pack_start(sw, expand=True)
        bbox = gtk.HButtonBox()
        bbox.pack_start(save)
        bbox.pack_start(delete)
        bbox.pack_start(refresh)
        bbox.pack_start(add)
        vbox.pack_start(bbox, expand=False)

        save.set_sensitive(False)
        add.set_sensitive(False)
        
        if os.path.exists(lyricname):
            buffer.set_text(file(lyricname).read())
        else:
            buffer.set_text("Searching for lyrics...")
            delete.set_sensitive(False)
            refresh.set_sensitive(False)
            add.set_sensitive(False)
            thread = threading.Thread(
                target=self.__search, args=(song, buffer, refresh, add))
            thread.setDaemon(True)
            thread.start()

        buffer.connect_object('changed', save.set_sensitive, True)

        self.add(vbox)
        self.set_default_size(400, 300)
        self.show_all()

    def __add(self, add, song):
        artist = song.comma('artist').encode('utf-8')
        title = song.comma('title').encode('utf-8')
        album = song.comma('album').encode('utf-8')
        
        util.website(
            "http://leoslyrics.com/submit.php?song=%s&artist=%s&album=%s" % (
            urllib.quote(title),
            urllib.quote(artist),
            urllib.quote(album)))
        add.set_sensitive(False)

    def __refresh(self, refresh, buffer, song):
        buffer.set_text("Searching for lyrics...\n\n")
        refresh.set_sensitive(False)
        thread = threading.Thread(
            target=self.__search, args=(song, buffer, refresh))
        thread.setDaemon(True)
        thread.start()

        
    def __search(self, song, buffer, refresh, add):
        artist = song.comma("artist")
        title = song.comma("title")
        self.songlist = []
        
        sock = urllib.urlopen(
            "http://api.leoslyrics.com/api_search.php?auth=QuodLibet&artist=%s&songtitle=%s"%(
            urllib.quote(artist.encode('utf-8')),
            urllib.quote(title.encode('utf-8'))))
        
        try: xmldoc = minidom.parse(sock).documentElement
        except:
            gobject.idle_add(buffer.set_text, "Server did not respond.")
            return

        sock.close()
        result_code = xmldoc.getElementsByTagName('response')[0].getAttribute('code')
        #print "Result code: ", result_code
        if result_code == '0': #success
            # This is 0 even if there are no matches.

            # We don't really need the top 100 matches, so I'm limiting it to ten
            matches = xmldoc.getElementsByTagName('result')[:10]
            songs = map(lambda x: x.getElementsByTagName('name')[0].firstChild.nodeValue +
			" - " +
			x.getElementsByTagName('title')[0].firstChild.nodeValue,
			matches)
            hids = map(lambda x: x.getAttribute('hid'), matches)

            if len(hids) == 0:
                #FIXME show other matches
                gobject.idle_add(buffer.set_text, 'Unable to find an exact ' +
                                 'match for this song. You can submit lyrics '+
                                 'for this song by clicking the Add button.')
                add.set_sensitive(True)
                return
             
            for i in range(len(hids)):
                self.songlist.append((songs[i], hids[i]))
                
            xmldoc.unlink()
            
            # Show the first match
            sock = urllib.urlopen(
                "http://api.leoslyrics.com/api_lyrics.php?auth=QuodLibet&hid=%s"%(
                urllib.quote(self.songlist[0][1].encode('utf-8'))))
            try: xmldoc = minidom.parse(sock).documentElement
            except:
                gobject.idle_add(buffer.set_text,
                                 "Unable to get the lyrics. " +
                                 "Please try again later.")
                return
            sock.close()
            text = xmldoc.getElementsByTagName('text')[0].firstChild.nodeValue
            xmldoc.unlink()

            text += "\n\nLyrics provided by leoslyrics.com"
            
            gobject.idle_add(buffer.set_text, text)
            gobject.idle_add(refresh.set_sensitive, True)
        else: #failed
            gobject.idle_add(buffer.set_text, "Server busy, try again later.")
            xmldoc.unlink()
            return

    def __lyricname(self, song):
        return util.fsencode(os.path.join(
            os.path.expanduser("~/.lyrics"),
            song.comma("artist").replace('/', '')[:64],
            song.comma("album").replace('/', '')[:64],
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

class NoLyricsFoundException(Exception): pass

plugin_song = LyricWindow
