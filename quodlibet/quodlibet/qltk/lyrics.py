# Copyright 2005 Eduardo Gonzalez, Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

# FIXME:
# - Too many buttons -- saving should be automatic?
# - Make purpose of 'Add' button clearer.
# - Indicate when the match was fuzzy in the buffer text.

import os
import threading
import urllib

import gobject
import gtk

from quodlibet import const
from quodlibet import qltk
from quodlibet import util

class LyricsPane(gtk.VBox):
    def __init__(self, song):
        # Commented code in this method is due to Lyric Wiki's disappearance.
        # See issue 273.
        super(LyricsPane, self).__init__(spacing=12)
        self.set_border_width(12)
        view = gtk.TextView()
        sw = gtk.ScrolledWindow()
        sw.add(view)
        refresh = qltk.Button(_("_Download"), gtk.STOCK_CONNECT)
        save = gtk.Button(stock=gtk.STOCK_SAVE)
        delete = gtk.Button(stock=gtk.STOCK_DELETE)
        add = gtk.Button(stock=gtk.STOCK_EDIT)
        view.set_wrap_mode(gtk.WRAP_WORD)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        lyricname = song.lyric_filename
        buffer = view.get_buffer()

        refresh.connect('clicked', self.__refresh, add, buffer, song)
        save.connect('clicked', self.__save, lyricname, buffer, delete)
        delete.connect('clicked', self.__delete, lyricname, save)
        add.connect('clicked', self.__add, song)

        sw.set_shadow_type(gtk.SHADOW_IN)
        self.pack_start(sw, expand=True)

        #self.pack_start(gtk.Label(_("Lyrics provided by %s.") %(
        #    "http://lyricwiki.org")), expand=False)

        bbox = gtk.HButtonBox()
        bbox.pack_start(save)
        bbox.pack_start(delete)
        #bbox.pack_start(refresh)
        bbox.pack_start(add)
        self.pack_start(bbox, expand=False)

        save.set_sensitive(False)
        add.set_sensitive(True)

        if os.path.exists(lyricname):
            buffer.set_text(file(lyricname).read())
        else:
            #buffer.set_text(_("No lyrics found.\n\nYou can click the "
            #                  "Download button to have Quod Libet search "
            #                  "for lyrics online.  You can also enter them "
            #                  "yourself and click save."))
            buffer.set_text(_("No lyrics found for this song."))
        buffer.connect_object('changed', save.set_sensitive, True)

    def __add(self, add, song):
        artist = song.comma('artist').encode('utf-8')

        util.website("http://lyricwiki.org/%s" % (urllib.quote(artist)))

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
                "http://lyricwiki.org/api.php?"
                "client=QuodLibet&func=getSong&artist=%s&song=%s&fmt=text"%(
                urllib.quote(artist.encode('utf-8')),
                urllib.quote(title.encode('utf-8'))))
            text = sock.read()
        except Exception, err:
            try: err = err.strerror.decode(const.ENCODING, 'replace')
            except: err = _("Unable to download lyrics.")
            gobject.idle_add(buffer.set_text, err)
            return

        sock.close()

        if text == 'Not found':
            gobject.idle_add(
                buffer.set_text, _("No lyrics found for this song."))
            return
        else:
            gobject.idle_add(buffer.set_text, text)
            gobject.idle_add(refresh.set_sensitive, True)

    def __save(self, save, lyricname, buffer, delete):
        try: os.makedirs(os.path.dirname(lyricname))
        except EnvironmentError, err: pass

        try: f = file(lyricname, "w")
        except EnvironmentError, err:
            print_w(err.strerror.decode(const.ENCODING, "replace"))
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
