# -*- coding: utf-8 -*-
# Copyright 2005 Eduardo Gonzalez, Joe Wreschnig
#           2017 Nick Boultbee
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

from gi.repository import Gtk, GLib

from quodlibet import _, print_d, print_w
from quodlibet.errorreport import errorhook
from quodlibet.formats import AudioFileError
from quodlibet import qltk
from quodlibet.qltk import Icons
from quodlibet import util
from quodlibet.util import connect_obj
from quodlibet.compat import quote, text_type
from quodlibet.util.urllib import urlopen


class LyricsPane(Gtk.VBox):
    def __init__(self, song):
        # Commented code in this method is due to Lyric Wiki's disappearance.
        # See issue 273.
        super(LyricsPane, self).__init__(spacing=12)
        self.set_border_width(12)
        view = Gtk.TextView()
        sw = Gtk.ScrolledWindow()
        sw.add(view)
        refresh = qltk.Button(_("_Download"))
        save = qltk.Button(_("_Save"), Icons.DOCUMENT_SAVE)
        delete = qltk.Button(_("_Delete"), Icons.EDIT_DELETE)
        add = qltk.Button(_("_Edit"), Icons.EDIT)
        view.set_wrap_mode(Gtk.WrapMode.WORD)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        buffer = view.get_buffer()

        refresh.connect('clicked', self.__refresh, add, buffer, song)
        save.connect('clicked', self.__save, song, buffer, delete)
        delete.connect('clicked', self.__delete, song, save)
        add.connect('clicked', self.__add, song)

        sw.set_shadow_type(Gtk.ShadowType.IN)
        self.pack_start(sw, True, True, 0)

        bbox = Gtk.HButtonBox()
        bbox.pack_start(save, True, True, 0)
        bbox.pack_start(delete, True, True, 0)
        #bbox.pack_start(refresh, True, True, 0)
        bbox.pack_start(add, True, True, 0)
        self.pack_start(bbox, False, True, 0)

        save.set_sensitive(False)
        add.set_sensitive(True)

        lyrics = song("~lyrics")

        if lyrics:
            buffer.set_text(lyrics)
        else:
            #buffer.set_text(_("No lyrics found.\n\nYou can click the "
            #                  "Download button to have Quod Libet search "
            #                  "for lyrics online.  You can also enter them "
            #                  "yourself and click save."))
            buffer.set_text(_("No lyrics found for this song."))
        connect_obj(buffer, 'changed', save.set_sensitive, True)

    def __add(self, add, song):
        artist = song.comma('artist').encode('utf-8')

        util.website("http://lyricwiki.org/%s" % (quote(artist)))

    def __refresh(self, refresh, add, buffer, song):
        buffer.set_text(_(u"Searching for lyrics…"))
        refresh.set_sensitive(False)
        thread = threading.Thread(
            target=self.__search, args=(song, buffer, refresh, add))
        thread.setDaemon(True)
        thread.start()

    def __search(self, song, buffer, refresh, add):
        artist = song.comma("artist")
        title = song.comma("title")

        try:
            sock = urlopen(
                "http://lyricwiki.org/api.php?"
                "client=QuodLibet&func=getSong&artist=%s&song=%s&fmt=text" % (
                quote(artist.encode('utf-8')),
                quote(title.encode('utf-8'))))
            text = sock.read()
        except Exception as err:
            util.print_exc()
            GLib.idle_add(buffer.set_text, text_type(err))
            return

        sock.close()

        if text == 'Not found':
            GLib.idle_add(
                buffer.set_text, _("No lyrics found for this song."))
            return
        else:
            GLib.idle_add(buffer.set_text, text.decode('utf-8'))
            GLib.idle_add(refresh.set_sensitive, True)

    def __save(self, save, song, buffer, delete):
        start, end = buffer.get_bounds()
        text = buffer.get_text(start, end, True)
        self._save_lyrics(song, text)
        delete.set_sensitive(True)
        save.set_sensitive(False)

    def _save_lyrics(self, song, text):
        # First, try writing to the tags.
        song["lyrics"] = (text.decode("utf-8") if isinstance(text, bytes)
                          else text)
        try:
            song.write()
        except AudioFileError as e:
            print_w("Couldn't write embedded lyrics (%s)" % e)
            self._save_to_file(song, text)
        else:
            self._delete_file(song.lyric_filename)

    def _save_to_file(self, song, text):
        lyricname = song.lyric_filename
        try:
            os.makedirs(os.path.dirname(lyricname), exist_ok=True)
        except EnvironmentError:
            errorhook()
        try:
            with open(lyricname, "w") as f:
                f.write(text)
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
