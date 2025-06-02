# Copyright 2005 Eduardo Gonzalez, Joe Wreschnig
#           2017-2022 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# FIXME: Too many buttons -- saving should be automatic?

import os
from urllib.parse import quote

from gi.repository import Gtk

from quodlibet import _, print_d, print_w, app
from quodlibet import qltk
from quodlibet import util
from quodlibet.errorreport import errorhook
from quodlibet.formats import AudioFileError
from quodlibet.qltk import Icons
from quodlibet.util import connect_obj


class LyricsPane(Gtk.Box):
    def __init__(self, song):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_border_width(12)
        view = Gtk.TextView()
        sw = Gtk.ScrolledWindow()
        sw.add(view)
        save = qltk.Button(_("_Save"), Icons.DOCUMENT_SAVE)
        delete = qltk.Button(_("_Delete"), Icons.EDIT_DELETE)
        view_online = qltk.Button(_("_View online"), Icons.APPLICATION_INTERNET)
        view.set_wrap_mode(Gtk.WrapMode.WORD)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        buffer = view.get_buffer()

        save.connect("clicked", self.__save, song, buffer, delete)
        delete.connect("clicked", self.__delete, song, save)
        view_online.connect("clicked", self.__view_online, song)

        sw.set_shadow_type(Gtk.ShadowType.IN)
        self.prepend(sw, True, True, 0)

        bbox = Gtk.HButtonBox()
        bbox.prepend(save, True, True, 0)
        bbox.prepend(delete, True, True, 0)
        bbox.prepend(view_online, True, True, 0)
        self.prepend(bbox, False, True, 0)

        save.set_sensitive(False)
        view_online.set_sensitive(True)

        lyrics = song("~lyrics")

        if lyrics:
            buffer.set_text(lyrics)
        else:
            buffer.set_text(_("No lyrics found for this song."))
        connect_obj(buffer, "changed", save.set_sensitive, True)

    def __view_online(self, add, song):
        # TODO: make this modular and plugin-friendly (#54, #3642 etc)
        def sanitise(s: str) -> str:
            return quote(
                s.replace(" ", "-")
                .replace(".", "")
                .replace("'", "")
                .replace('"', "")
                .replace(",", "-")
                .lower()
                .encode("utf-8")
            )

        artist = sanitise(song.list("artist")[0])
        title = sanitise(song.comma("title"))
        util.website(f"https://genius.com/{artist}-{title}-lyrics")

    def __save(self, save, song, buffer, delete):
        start, end = buffer.get_bounds()
        text = buffer.get_text(start, end, True)
        self._save_lyrics(song, text)
        delete.set_sensitive(True)
        save.set_sensitive(False)

    def _save_lyrics(self, song, text):
        # First, try writing to the tags.
        if "lyrics" not in song and "unsyncedlyrics" in song:
            tag = "unsyncedlyrics"
        else:
            tag = "lyrics"
        song[tag] = text
        try:
            song.write()
        except AudioFileError as e:
            print_w(f"Couldn't write embedded lyrics ({e!r})")
            self._save_to_file(song, text)
        else:
            print_d(f"Wrote embedded lyrics into {song('~filename')}")
            app.librarian.emit("changed", [song])
            fn = song.lyric_filename
            if fn:
                self._delete_file(fn)

    def _save_to_file(self, song, text):
        lyric_fn = song.lyric_filename
        if not lyric_fn:
            print_w("No lyrics file to save to, ignoring.")
            return
        try:
            os.makedirs(os.path.dirname(lyric_fn), exist_ok=True)
        except OSError:
            errorhook()
        try:
            with open(lyric_fn, "wb") as f:
                f.write(text.encode("utf-8"))
            print_d(f"Saved lyrics to file {lyric_fn!r}")
        except OSError:
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
        if not filename:
            return
        try:
            os.unlink(filename)
            print_d(f"Removed lyrics file {filename!r}")
        except OSError:
            pass
        lyric_dir = os.path.dirname(filename)
        try:
            os.rmdir(lyric_dir)
            print_d(f"Removed lyrics directory {lyric_dir}")
        except OSError:
            pass
