# Copyright 2005 Eduardo Gonzalez, Joe Wreschnig
#           2017-2025 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# FIXME: Too many buttons -- saving should be automatic?

import os
from pathlib import Path
from urllib.parse import quote

from gi.repository import Gtk

from quodlibet import _, print_d, print_w, app
from quodlibet import qltk
from quodlibet import util
from quodlibet.errorreport import errorhook
from quodlibet.formats import AudioFileError, AudioFile
from quodlibet.qltk import Icons, add_css
from quodlibet.util import connect_obj


class LyricsPane(Gtk.VBox):
    def __init__(self, parent, _library):
        super().__init__(spacing=12, margin=12)
        self.song = None
        self.title = _("Lyrics")
        self.text_view = view = Gtk.TextView()
        sw = Gtk.ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.IN)
        sw.add(view)
        self.save = save = qltk.Button(_("_Save"), Icons.DOCUMENT_SAVE)
        self.delete = delete = qltk.Button(_("_Delete"), Icons.EDIT_DELETE)
        view_online = qltk.Button(_("_View online"), Icons.APPLICATION_INTERNET)
        view.set_wrap_mode(Gtk.WrapMode.WORD)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.buffer = buffer = view.get_buffer()

        save.connect("clicked", self.__save, buffer, delete)
        delete.connect("clicked", self.__delete, save)
        view_online.connect("clicked", self.__view_online)

        self.pack_start(sw, True, True, 0)

        bbox = Gtk.Box(spacing=9, orientation=Gtk.Orientation.HORIZONTAL)
        bbox.set_homogeneous(True)
        bbox.pack_start(view_online, False, True, 0)
        bbox.pack_start(delete, False, True, 0)
        bbox.pack_start(save, False, True, 0)
        box2 = Gtk.Box()
        box2.props.halign = Gtk.Align.END
        box2.pack_start(bbox, True, False, 0)
        self.pack_start(box2, False, False, 0)
        add_css(sw, "scrolledwindow { padding: 0px 6px; }")
        connect_obj(buffer, "changed", save.set_sensitive, True)
        parent.connect("changed", self.__parent_changed)

    def __parent_changed(self, parent, songs: list[AudioFile]):
        if len(songs) == 1:
            self._set_enabled(True)

            self.song = songs[0]
            lyrics = self.song("~lyrics")

            if lyrics:
                self.buffer.set_text(lyrics)
                self.delete.set_sensitive(True)
                self.delete.set_tooltip_text(
                    _("Delete the saved lyrics from this song")
                )
                self.text_view.set_tooltip_text(None)
            else:
                self.buffer.set_text("")
                self.text_view.set_tooltip_text("Enter lyrics here")
                self.save.set_sensitive(False)
                self.delete.set_sensitive(False)
                self.delete.set_tooltip_text(None)

        else:
            self.song = None
            msg = _("Select a single track to edit its lyrics")
            self.text_view.set_tooltip_text(msg)
            self.buffer.set_text("")
            self._set_enabled(False)

    def _set_enabled(self, value: bool) -> None:
        self.set_sensitive(value)
        self.text_view.set_sensitive(value)

    def __view_online(self, add):
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

        artist = sanitise(self.song.list("artist")[0])
        title = sanitise(self.song.comma("title"))
        util.website(f"https://genius.com/{artist}-{title}-lyrics")

    def __save(self, save, buffer, delete):
        start, end = buffer.get_bounds()
        text = buffer.get_text(start, end, True)
        self._save_lyrics(self.song, text)
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
            path = song.lyrics_path
            if path:
                self._delete_file(path)

    def _save_to_file(self, song, text):
        lyric_fn = song.lyrics_path
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

    def __delete(self, delete, save):
        if (song := self.song) is None:
            return
        # First, delete lyrics from the tags.
        song.remove("lyrics")
        try:
            song.write()
        except AudioFileError:
            util.print_exc()
        else:
            app.librarian.emit("changed", [song])
        self._delete_file(song.lyrics_path)
        self.text_view.get_buffer().set_text("")
        delete.set_sensitive(False)
        save.set_sensitive(True)

    def _delete_file(self, path: Path):
        if not path:
            return
        try:
            path.unlink()
        except OSError:
            pass
        else:
            print_d(f"Removed lyrics file {path!s}")
        lyric_dir = path.parent
        try:
            lyric_dir.rmdir()
        except OSError:
            pass
        else:
            print_d(f"Removed lyrics directory {lyric_dir!s}")
