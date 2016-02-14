# -*- coding: utf-8 -*-
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

from gi.repository import Gtk, GLib

from quodlibet import qltk
from quodlibet.qltk import Icons
from quodlibet import util
from quodlibet.util import connect_obj


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

        util.website("http://lyricwiki.org/%s" % (urllib.quote(artist)))

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
            sock = urllib.urlopen(
                "http://lyricwiki.org/api.php?"
                "client=QuodLibet&func=getSong&artist=%s&song=%s&fmt=text" % (
                urllib.quote(artist.encode('utf-8')),
                urllib.quote(title.encode('utf-8'))))
            text = sock.read()
        except Exception as err:
            encoding = util.get_locale_encoding()
            try:
                err = err.strerror.decode(encoding, 'replace')
            except:
                err = _("Unable to download lyrics.")
            GLib.idle_add(buffer.set_text, err)
            return

        sock.close()

        if text == 'Not found':
            GLib.idle_add(
                buffer.set_text, _("No lyrics found for this song."))
            return
        else:
            GLib.idle_add(buffer.set_text, text)
            GLib.idle_add(refresh.set_sensitive, True)

    def __save(self, save, song, buffer, delete):
        start, end = buffer.get_bounds()
        text = buffer.get_text(start, end, True)

        # First, write back to the tags.
        song["lyrics"] = text.decode("utf-8")
        song.write()

        # Then, write to file.
        # TODO: write to file only if could not write to tags, otherwise delete
        # the file.
        lyricname = song.lyric_filename
        try:
            os.makedirs(os.path.dirname(lyricname))
        except EnvironmentError as err:
            pass

        try:
            with open(lyricname, "w") as f:
                f.write(text)
        except EnvironmentError as err:
            encoding = util.get_locale_encoding()
            print_w(err.strerror.decode(encoding, "replace"))
        delete.set_sensitive(True)
        save.set_sensitive(False)

    def __delete(self, delete, song, save):
        # First, delete from the tags.
        song.remove("lyrics")
        song.write()

        # Then, delete the file.
        lyricname = song.lyric_filename
        try:
            os.unlink(lyricname)
        except EnvironmentError:
            pass
        lyricname = os.path.dirname(lyricname)
        try:
            os.rmdir(lyricname)
        except EnvironmentError:
            pass
        delete.set_sensitive(False)
        save.set_sensitive(True)
