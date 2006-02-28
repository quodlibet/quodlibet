# Copyright 2005 Eduardo Gonzalez, Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

# FIXME:
# - Too many buttons -- saving should be automatic?
# - Make purpose of 'Add' button clearer.
# - Indicate when the match was fuzzy in the buffer text.

import os
import locale
import threading
import urllib
import gtk, gobject
import qltk
import util

from xml.dom import minidom

class LyricsPane(gtk.VBox):
    def __init__(self, song):
        super(LyricsPane, self).__init__(spacing=12)
        self.set_border_width(12)
        view = gtk.TextView()
        sw = gtk.ScrolledWindow()
        sw.add(view)
        refresh = qltk.Button(_("_Download"), gtk.STOCK_CONNECT)
        save = gtk.Button(stock=gtk.STOCK_SAVE)
        delete = gtk.Button(stock=gtk.STOCK_DELETE)
        add = gtk.Button(stock=gtk.STOCK_ADD)
        view.set_wrap_mode(gtk.WRAP_WORD)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        lyricname = self.__lyricname(song)
        buffer = view.get_buffer()

        refresh.connect('clicked', self.__refresh, add, buffer, song)
        save.connect('clicked', self.__save, lyricname, buffer, delete)
        delete.connect('clicked', self.__delete, lyricname, save)
        add.connect('clicked', self.__add, song)

        sw.set_shadow_type(gtk.SHADOW_IN)
        self.pack_start(sw, expand=True)

        self.pack_start(gtk.Label(_("Lyrics provided by %s.") %(
            "http://www.leoslyrics.com")), expand=False)

        bbox = gtk.HButtonBox()
        bbox.pack_start(save)
        bbox.pack_start(delete)
        bbox.pack_start(refresh)
        bbox.pack_start(add)
        self.pack_start(bbox, expand=False)

        save.set_sensitive(False)
        add.set_sensitive(False)
        
        if os.path.exists(lyricname): buffer.set_text(file(lyricname).read())
        else: buffer.set_text(_("No lyrics found.\n\nYou can click the " 
                                "Download button to have Quod Libet search "
                                "for lyrics online.  You can also enter them "
                                "yourself and click save."))
        buffer.connect_object('changed', save.set_sensitive, True)

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

    def __refresh(self, refresh, add, buffer, song):
        buffer.set_text(_("Searching for lyrics..."))
        refresh.set_sensitive(False)
        thread = threading.Thread(
            target=self.__search, args=(song, buffer, refresh, add))
        thread.setDaemon(True)
        thread.start()
        
    def __search(self, song, buffer, refresh, add):
        artist = song.comma("artist")
        title = song.comma("title")
        
        try:
            sock = urllib.urlopen(
                "http://api.leoslyrics.com/api_search.php?auth="
                "QuodLibet&artist=%s&songtitle=%s"%(
                urllib.quote(artist.encode('utf-8')),
                urllib.quote(title.encode('utf-8'))))        
            xmldoc = minidom.parse(sock).documentElement
        except Exception, err:
            try: err = err.strerror.decode(locale.getpreferredencoding())
            except: err = _("Unable to download lyrics.")
            gobject.idle_add(buffer.set_text, err)
            return

        sock.close()
        result_code = xmldoc.getElementsByTagName(
            'response')[0].getAttribute('code')

        if result_code == '0': # This is success even if there are no matches.
            # Grab the first 10 results.
            matches = xmldoc.getElementsByTagName('result')[:10]
            hids = map(lambda x: x.getAttribute('hid'), matches)
            exacts = map(lambda x: x.getAttribute('exactMatch'), matches)
            
            if len(hids) == 0:
                gobject.idle_add(
                    buffer.set_text, _("No lyrics found for this song."))
                add.set_sensitive(True)
                return
             
            songlist = zip(hids, exacts)
                
            xmldoc.unlink()
            
            # Show the first match
            try:
                sock = urllib.urlopen(
                    "http://api.leoslyrics.com/api_lyrics.php?auth="
                    "QuodLibet&hid=%s"%(
                    urllib.quote(songlist[0][0].encode('utf-8'))))
                xmldoc = minidom.parse(sock).documentElement
            except Exception, err:
                try: err = err.strerror.decode(locale.getpreferredencoding())
                except: err = _("Unable to download lyrics.")
                gobject.idle_add(buffer.set_text, err)
                return
            sock.close()

            text = xmldoc.getElementsByTagName('text')[0].firstChild.nodeValue
            xmldoc.unlink()

            gobject.idle_add(buffer.set_text, text)
            gobject.idle_add(refresh.set_sensitive, True)
            gobject.idle_add(add.set_sensitive, songlist[0][1] == 'false')

        else:
            gobject.idle_add(buffer.set_text, _("Unable to download lyrics."))
            xmldoc.unlink()
            return

    def __lyricname(self, song):
        return util.fsencode(os.path.join(
            os.path.expanduser("~/.lyrics"),
            song.comma("artist").replace('/', '')[:128],
            song.comma("title").replace('/', '')[:128] + '.lyric'))

    def __save(self, save, lyricname, buffer, delete):
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
        lyricname = os.path.dirname(lyricname)
        try: os.rmdir(lyricname)
        except EnvironmentError: pass
        delete.set_sensitive(False)
        save.set_sensitive(True)
