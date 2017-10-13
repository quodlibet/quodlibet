# -*- coding: utf-8 -*-
# Copyright 2005 Eduardo Gonzalez, Joe Wreschnig
#           2017 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

# FIXME:
# - Too many buttons -- saving should be automatic?

import os
import threading

from gi.repository import Gtk

from quodlibet import _, print_d, print_w, app
from quodlibet import qltk
from quodlibet import util
from quodlibet.compat import quote
from quodlibet.errorreport import errorhook
from quodlibet.formats import AudioFileError
from quodlibet.qltk import Icons
from quodlibet.util import connect_obj


class LyricsPane(Gtk.VBox):
    def __init__(self, song):
        super(LyricsPane, self).__init__(spacing=12)
        self.set_border_width(12)
        view = Gtk.TextView()
        sw = Gtk.ScrolledWindow()
        sw.add(view)
        save = qltk.Button(_("_Save"), Icons.DOCUMENT_SAVE)
        delete = qltk.Button(_("_Delete"), Icons.EDIT_DELETE)
        view_online = qltk.Button(_("_View online"),
                                  Icons.APPLICATION_INTERNET)
        view.set_wrap_mode(Gtk.WrapMode.WORD)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        buffer = view.get_buffer()

        save.connect('clicked', self.__save, song, buffer, delete)
        delete.connect('clicked', self.__delete, song, save)
        view_online.connect('clicked', self.__view_online, song)

        sw.set_shadow_type(Gtk.ShadowType.IN)
        self.pack_start(sw, True, True, 0)

        bbox = Gtk.HButtonBox()
        bbox.pack_start(save, True, True, 0)
        bbox.pack_start(delete, True, True, 0)
        bbox.pack_start(view_online, True, True, 0)
        self.pack_start(bbox, False, True, 0)

        save.set_sensitive(False)
        view_online.set_sensitive(True)

        lyrics = song("~lyrics")

        if lyrics:
            buffer.set_text(lyrics)
        else:
            buffer.set_text(_("No lyrics found for this song."))
        connect_obj(buffer, 'changed', save.set_sensitive, True)

    def __view_online(self, add, song):
        artist = song.comma('artist').encode('utf-8')
        title = song.comma('title').encode('utf-8')

        util.website("http://lyrics.wikia.com/%s:%s"
                     % (quote(artist), quote(title)))

    def __refresh(self, refresh, add, buffer, song):
        buffer.set_text(_(u"Searching for lyrics…"))
        refresh.set_sensitive(False)
        thread = threading.Thread(
            target=self.__search, args=(song, buffer, refresh, add))
        thread.setDaemon(True)
        thread.start()

    def __save(self, save, song, buffer, delete):
        start, end = buffer.get_bounds()
        text = util.gdecode(buffer.get_text(start, end, True))
        self._save_lyrics(song, text)
        delete.set_sensitive(True)
        save.set_sensitive(False)

    def _save_lyrics(self, song, text):
        # First, try writing to the tags.
        song["lyrics"] = text
        try:
            song.write()
        except AudioFileError as e:
            print_w("Couldn't write embedded lyrics (%s)" % e)
            self._save_to_file(song, text)
        else:
            print_d("Wrote embedded lyrics into %s" % song("~filename"))
            app.librarian.emit('changed', [song])
            self._delete_file(song.lyric_filename)

    def _save_to_file(self, song, text):
        lyricname = song.lyric_filename
        try:
            os.makedirs(os.path.dirname(lyricname), exist_ok=True)
        except EnvironmentError:
            errorhook()
        try:
            with open(lyricname, "wb") as f:
                f.write(text.encode("utf-8"))
            print_d("Saved lyrics to file (%s)" % lyricname)
        except EnvironmentError:
            errorhook()

    def __delete(self, delete, song, save):
        # First, delete from the tags.
        song.remove("lyrics")
        try:
            song.write()
        except AudioFileError:
            util.print_exc()

        self._delete_file(song.lyric_filename)
        delete.set_sensitive(False)
        save.set_sensitive(True)

    def _delete_file(self, filename):
        try:
            os.unlink(filename)
            print_d("Removed lyrics file '%s'" % filename)
        except EnvironmentError:
            pass
        lyric_dir = os.path.dirname(filename)
        try:
            os.rmdir(lyric_dir)
            print_d("Removed lyrics directory '%s'" % lyric_dir)
        except EnvironmentError:
            pass
