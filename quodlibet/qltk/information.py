# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2016-2022 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import time
from collections import defaultdict

from gi.repository import Gtk, Pango

from quodlibet.formats import PEOPLE
from senf import fsn2text

from quodlibet import ngettext, _
from quodlibet import qltk
from quodlibet import util
from quodlibet import app

from quodlibet.qltk.bookmarks import EditBookmarksPane
from quodlibet.qltk.cover import CoverImage
from quodlibet.qltk.lyrics import LyricsPane
from quodlibet.qltk.window import Window, PersistentWindowMixin
from quodlibet.qltk.x import Align
from quodlibet.util import tag, connect_destroy
from quodlibet.util.i18n import numeric_phrase
from quodlibet.util.tags import readable
from quodlibet.util.path import filesize, unexpand


def Label(label=None, markup=None, ellipsize=False):
    if markup:
        l = Gtk.Label()
        l.set_markup(markup)
    else:
        l = Gtk.Label(label=label)
    l.set_selectable(True)
    l.set_alignment(0, 0)
    if ellipsize:
        l.set_ellipsize(Pango.EllipsizeMode.END)
    return l


class TitleLabel(Gtk.Label):
    def __init__(self, text, is_markup=False):
        super().__init__()
        self.set_ellipsize(Pango.EllipsizeMode.END)
        markup = text if is_markup else (util.italic(text))
        markup = f"<span size='xx-large'>{markup}</span>"
        self.set_markup(markup)
        self.set_selectable(True)


class ReactiveCoverImage(CoverImage):
    def __init__(self, resize=False, size=125, song=None, tooltip=None):
        super().__init__(resize, size, song)
        self.set_property("no-show-all", True)

        def show_cover(cover, success):
            if success:
                cover.show()
            cover.disconnect(signal_id)

        signal_id = self.connect("cover-visible", show_cover)
        self.set_song(song)
        if tooltip:
            self.get_child().set_tooltip_text(tooltip)


def Frame(name, widget):
    def hx(value):
        return hex(int(value * 255))[2:]

    f = Gtk.Frame()
    qltk.add_css(f, "* {opacity: 0.9}")
    l = Gtk.Label()
    l.set_markup(util.escape(name))
    qltk.add_css(l, " * {opacity: 0.6; padding: 0px 2px;}")
    f.set_label_widget(l)
    a = Align(top=6, left=12, bottom=6, right=6)
    f.add(a)
    a.add(widget)
    return f


def Table(rows):
    # Gtk.Table doesn't allow 0 rows
    t = Gtk.Table(n_rows=max(rows, 1), n_columns=2)
    t.set_col_spacings(6)
    t.set_row_spacings(6)
    t.set_homogeneous(False)
    return t


def SW():
    swin = Gtk.ScrolledWindow()
    swin.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    return swin


class NoSongs(Gtk.Label):
    def __init__(self):
        super().__init__(label=_("No songs are selected."))
        self.title = _("No Songs")


class OneSong(qltk.Notebook):
    def __init__(self, library, song, lyrics=True, bookmarks=True):
        super().__init__()
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        vbox.set_border_width(12)
        self._title(song, vbox)
        self._album(song, vbox)
        self._people(song, vbox)
        self._library(song, vbox)
        self._file(song, vbox)
        self._additional(song, vbox)
        sw = SW()
        sw.title = _("Information")
        sw.add_with_viewport(vbox)
        self.append_page(sw)
        if lyrics:
            lyrics = LyricsPane(song)
            lyrics.title = _("Lyrics")
            self.append_page(lyrics)

        if bookmarks:
            bookmarks = EditBookmarksPane(None, song)
            bookmarks.title = _("Bookmarks")
            bookmarks.set_border_width(12)
            self.append_page(bookmarks)

        connect_destroy(library, "changed", self.__check_changed, vbox, song)

    def _switch_to_lyrics(self):
        self.set_current_page(1)

    def __check_changed(self, library, songs, vbox, song):
        if song in songs:
            for c in vbox.get_children():
                vbox.remove(c)
                c.destroy()
            self._title(song, vbox)
            self._album(song, vbox)
            self._people(song, vbox)
            self._library(song, vbox)
            self._file(song, vbox)
            self._additional(song, vbox)
            parent = qltk.get_top_parent(self)
            if parent:
                parent.set_title(self.title + " - Quod Libet")
            vbox.show_all()

    def _title(self, song, box):
        text = song.comma("title")
        if "version" in song:
            text += "\n" + util.escape(song.comma("version"))
        box.prepend(TitleLabel(text), False, False, 0)
        self.title = song.comma("title")

    def _album(self, song, box):
        if "album" not in song:
            return
        text = [f"<span size='x-large'>{util.italic(song.comma('album'))}</span>"]
        secondary = []
        if "discnumber" in song:
            secondary.append(_("Disc %s") % song["discnumber"])
        if "discsubtitle" in song:
            secondary.append(util.italic(song.comma("discsubtitle")))
        if "tracknumber" in song:
            secondary.append(_("Track %s") % song["tracknumber"])
        if secondary:
            text.append(" - ".join(secondary))

        if "date" in song:
            text.append(util.escape(song.comma("date")))

        if "organization" in song or "labelid" in song:
            t = util.escape(song.comma("~organization~labelid"))
            text.append(t)

        if "producer" in song:
            text.append(_("Produced by %s") % (util.escape(song.comma("producer"))))

        w = Label(markup="\n".join(text), ellipsize=True)
        hb = Gtk.Box(spacing=12)

        hb.prepend(w, True, True, 0)
        box.prepend(Frame(tag("album"), hb), False, False, 0)

        cover = ReactiveCoverImage(song=song)
        hb.prepend(cover, False, True, 0)

    def _people(self, song, box):
        data = []
        if "artist" in song:
            title = _("artist") if len(song.list("artist")) == 1 else _("artists")
            title = util.capitalize(title)
            data.append((title, song["artist"]))
        for tag_ in [
            "performer",
            "lyricist",
            "arranger",
            "composer",
            "conductor",
            "author",
        ]:
            if tag_ in song:
                name = (
                    tag(tag_)
                    if len(song.list(tag_)) == 1
                    else readable(tag_, plural=True)
                )
                data.append((name, song[tag_]))
        performers = defaultdict(list)
        for tag_ in song:
            if "performer:" in tag_:
                for person in song.list(tag_):
                    role = util.title(tag_.split(":", 1)[1])
                    performers[role].append(person)

        if performers:
            text = "\n".join(
                "{} ({})".format(", ".join(names), part)
                for part, names in performers.items()
            )

            name = tag("performer") if len(performers) == 1 else _("performers")
            data.append((name, text))

        table = Table(len(data))
        for i, (key, text) in enumerate(data):
            key = util.capitalize(util.escape(key) + ":")
            table.attach(
                Label(markup=key), 0, 1, i, i + 1, xoptions=Gtk.AttachOptions.FILL
            )
            label = Label(text, ellipsize=True)
            table.attach(label, 1, 2, i, i + 1)
        box.prepend(Frame(tag("~people"), table), False, False, 0)

    def _library(self, song, box):
        def counter(i):
            return (
                _("Never")
                if i == 0
                else numeric_phrase("%(n)d time", "%(n)d times", i, "n")
            )

        def ftime(t):
            if t == 0:
                return _("Unknown")
            return str(time.strftime("%c", time.localtime(t)))

        playcount = counter(song.get("~#playcount", 0))
        skipcount = counter(song.get("~#skipcount", 0))
        lastplayed = ftime(song.get("~#lastplayed", 0))
        if lastplayed == _("Unknown"):
            lastplayed = _("Never")
        added = ftime(song.get("~#added", 0))
        rating = song("~rating")
        has_rating = "~#rating" in song

        t = Table(5)
        table = [
            (_("added"), added, True),
            (_("last played"), lastplayed, True),
            (_("plays"), playcount, True),
            (_("skips"), skipcount, True),
            (_("rating"), rating, has_rating),
        ]

        for i, (l, r, s) in enumerate(table):
            l = util.capitalize(l + ":")
            lab = Label(l)
            t.attach(lab, 0, 1, i + 1, i + 2, xoptions=Gtk.AttachOptions.FILL)
            label = Label(r)
            label.set_sensitive(s)
            t.attach(label, 1, 2, i + 1, i + 2)

        box.prepend(Frame(_("Library"), t), False, False, 0)

    def _file(self, song, box):
        def ftime(t):
            if t == 0:
                return _("Unknown")
            return str(time.strftime("%c", time.localtime(t)))

        fn = fsn2text(unexpand(song["~filename"]))
        length = util.format_time_preferred(song.get("~#length", 0))
        size = util.format_size(song.get("~#filesize") or filesize(song["~filename"]))
        mtime = ftime(util.path.mtime(song["~filename"]))
        format_ = song("~format")
        codec = song("~codec")
        encoding = song.comma("~encoding")
        bitrate = song("~bitrate")

        table = [
            (_("path"), fn),
            (_("length"), length),
            (_("format"), format_),
            (_("codec"), codec),
            (_("encoding"), encoding),
            (_("bitrate"), bitrate),
            (_("file size"), size),
            (_("modified"), mtime),
        ]
        t = Table(len(table))

        for i, (tag_, text) in enumerate(table):
            tag_ = util.capitalize(util.escape(tag_) + ":")
            lab = Label(text)
            lab.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
            t.attach(Label(tag_), 0, 1, i, i + 1, xoptions=Gtk.AttachOptions.FILL)
            t.attach(lab, 1, 2, i, i + 1)

        box.prepend(Frame(_("File"), t), False, False, 0)

    def _additional(self, song, box):
        if "website" not in song and "comment" not in song:
            return
        markup_data = []

        if "comment" in song:
            comments = song.list("comment")
            markups = [util.italic(c) for c in comments]
            markup_data.append(("comment", markups))

        if "website" in song:
            markups = [
                f'<a href="{util.escape(website)}">{util.escape(website)}</a>'
                for website in song.list("website")
            ]
            markup_data.append(("website", markups))

        table = Table(1)
        for i, (key, markups) in enumerate(markup_data):
            title = readable(key, plural=len(markups) > 1)
            lab = Label(markup=util.capitalize(util.escape(title) + ":"))
            table.attach(lab, 0, 1, i, i + 1, xoptions=Gtk.AttachOptions.FILL)
            lab = Label(markup="\n".join(markups), ellipsize=True)
            table.attach(lab, 1, 2, i, i + 1)
        box.prepend(Frame(_("Additional"), table), False, False, 0)


class OneAlbum(qltk.Notebook):
    def __init__(self, songs):
        super().__init__()
        swin = SW()
        swin.title = _("Information")
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        vbox.set_border_width(12)
        swin.add_with_viewport(vbox)
        # Needed to get proper track/disc/part ordering
        songs = sorted(songs)
        self._title(songs, vbox)
        self._album(songs, vbox)
        self._people(songs, vbox)
        self._description(songs, vbox)
        self.append_page(swin)

    def _title(self, songs, box):
        song = songs[0]
        self.title = text = song["album"]
        markup = util.italic(text)
        if "date" in song:
            markup += " <small>({})</small>".format(util.escape(song("~year")))
        box.prepend(TitleLabel(markup, is_markup=True), False, False, 0)

    def _album(self, songs, box):
        text = []

        discs = {}
        for song in songs:
            try:
                discs[song("~#disc")] = int(song["tracknumber"].split("/")[1])
            except (AttributeError, ValueError, IndexError, KeyError):
                discs[song("~#disc")] = max(
                    [song("~#track", discs.get(song("~#disc"), 0))]
                )
        tracks = sum(discs.values())
        discs = len(discs)
        length = sum([song.get("~#length", 0) for song in songs])

        if tracks == 0 or tracks < len(songs):
            tracks = len(songs)

        parts = []
        if discs > 1:
            parts.append(ngettext("%d disc", "%d discs", discs) % discs)
        parts.append(ngettext("%d track", "%d tracks", tracks) % tracks)
        if tracks != len(songs):
            parts.append(
                ngettext("%d selected", "%d selected", len(songs)) % len(songs)
            )

        text.append(", ".join(parts))
        text.append(f"({util.format_time_preferred(length)})")

        if "location" in song:
            text.append(util.escape(song["location"]))
        if "organization" in song or "labelid" in song:
            t = util.escape(song.comma("~organization~labelid"))
            text.append(t)

        if "producer" in song:
            text.append(_("Produced by %s") % (util.escape(song.comma("producer"))))

        w = Label(markup="\n".join(text), ellipsize=True)
        hb = Gtk.Box(spacing=12)
        hb.prepend(w, True, True, 0)
        hb.prepend(ReactiveCoverImage(song=song), False, True, 0)

        box.prepend(hb, False, False, 0)

    def _people(self, songs, box):
        tags_ = PEOPLE
        people = defaultdict(set)

        for song in songs:
            for t in tags_:
                if t in song:
                    people[t] |= set(song.list(t))

        data = []
        # Preserve order of people
        for tag_ in tags_:
            values = people.get(tag_)
            if values:
                name = readable(tag_, plural=len(values) > 1)
                data.append((name, "\n".join(values)))

        table = Table(len(data))
        for i, (key, text) in enumerate(data):
            key = util.capitalize(util.escape(key) + ":")
            table.attach(
                Label(markup=key), 0, 1, i, i + 1, xoptions=Gtk.AttachOptions.FILL
            )
            label = Label(text, ellipsize=True)
            table.attach(label, 1, 2, i, i + 1)
        box.prepend(Frame(tag("~people"), table), False, False, 0)

    def _description(self, songs, box):
        text = []
        cur_disc = songs[0]("~#disc", 1) - 1
        cur_part = None
        cur_track = songs[0]("~#track", 1) - 1
        for song in songs:
            track = song("~#track", 0)
            disc = song("~#disc", 0)
            part = song.get("part")
            if disc != cur_disc:
                if cur_disc:
                    text.append("")
                cur_track = song("~#track", 1) - 1
                cur_part = None
                cur_disc = disc
                if disc:
                    text.append("%s" % (_("Disc %s") % disc))
            if part != cur_part:
                ts = "    " * bool(disc)
                cur_part = part
                if part:
                    text.append(f"{ts}{util.escape(part)}")
            cur_track += 1
            ts = "    " * (bool(disc) + bool(part))
            while cur_track < track:
                text.append(
                    "{ts}{cur: >2}. {text}".format(
                        ts=ts, cur=cur_track, text=_("Track unavailable")
                    )
                )
                cur_track += 1
            title = util.italic(song.comma("~title~version"))
            text.append(f"{ts}{track: >2}. {title}")
        l = Label(markup="\n".join(text), ellipsize=True)
        box.prepend(Frame(_("Track List"), l), False, False, 0)


class OneArtist(qltk.Notebook):
    def __init__(self, songs):
        super().__init__()
        swin = SW()
        swin.title = _("Information")
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        vbox.set_border_width(12)
        swin.add_with_viewport(vbox)
        self._title(songs, vbox)
        self._album(songs, vbox)
        self.append_page(swin)

    def _title(self, songs, box):
        self.title = songs[0]("artist")
        l = TitleLabel(self.title)
        box.prepend(l, False, False, 0)

    def _album(self, songs, box):
        albums, noalbum = _sort_albums(songs)

        def format(args):
            date, song, album = args
            markup = f"<big>{util.italic(album)}</big>"
            return f"{markup} ({date[:4]})" if date else markup

        get_cover = app.cover_manager.get_cover
        covers = [(a, get_cover(s), s) for d, s, a in albums]
        albums = [format(a) for a in albums]
        if noalbum:
            albums.append(
                ngettext("%d song with no album", "%d songs with no album", noalbum)
                % noalbum
            )
        l = Label(markup="\n".join(albums), ellipsize=True)
        box.prepend(Frame(_("Selected Discography"), l), False, False, 0)

        covers = [ac for ac in covers if bool(ac[1])]
        t = Gtk.Table(n_rows=4, n_columns=(len(covers) // 4) + 1)
        t.set_col_spacings(12)
        t.set_row_spacings(12)
        added = set()
        for i, (album, cover, song) in enumerate(covers):
            if cover.name in added:
                continue
            cov = ReactiveCoverImage(song=song, tooltip=album)
            c = i % 4
            r = i // 4
            t.attach(
                cov, c, c + 1, r, r + 1, xoptions=Gtk.AttachOptions.EXPAND, yoptions=0
            )
            added.add(cover.name)
        box.prepend(t, True, True, 0)


def _sort_albums(songs):
    """:return: a tuple of (albums, count) where
    count is the number of album-less songs and
    albums is a list of (date, song, album), sorted"""
    no_album_count = 0
    albums = {}
    for song in songs:
        if "album" in song:
            albums[song.list("album")[0]] = song
        else:
            no_album_count += 1
    albums = [(song.get("date", ""), song, album) for album, song in albums.items()]
    albums.sort()
    return albums, no_album_count


class ManySongs(qltk.Notebook):
    def __init__(self, songs):
        super().__init__()
        swin = SW()
        swin.title = _("Information")
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        vbox.set_border_width(12)
        swin.add_with_viewport(vbox)
        self._title(songs, vbox)
        self._people(songs, vbox)
        self._album(songs, vbox)
        self._file(songs, vbox)
        self.append_page(swin)

    def _title(self, songs, box):
        self.title = ngettext("%d song", "%d songs", len(songs)) % len(songs)
        markup = util.escape(self.title)
        box.prepend(TitleLabel(markup, is_markup=True), False, False, 0)

    def _people(self, songs, box):
        artists = set()
        none = 0
        for song in songs:
            if "artist" in song:
                artists.update(song.list("artist"))
            else:
                none += 1
        artists = sorted(artists)
        num_artists = len(artists)

        if none:
            artists.append(
                ngettext("%d song with no artist", "%d songs with no artist", none)
                % none
            )
        label = Label(markup=util.escape("\n".join(artists)), ellipsize=True)
        frame = Frame("%s (%d)" % (util.capitalize(_("artists")), num_artists), label)
        box.prepend(frame, False, False, 0)

    def _album(self, songs, box):
        albums = set()
        none = 0
        for song in songs:
            if "album" in song:
                albums.update(song.list("album"))
            else:
                none += 1
        albums = sorted(albums)
        num_albums = len(albums)

        markup = "\n".join(util.italic(a) for a in albums)
        if none:
            text = (
                ngettext("%d song with no album", "%d songs with no album", none) % none
            )
            markup += f"\n{util.escape(text)}"

        label = Label()
        label.set_markup(markup)
        albums = util.capitalize(_("albums"))
        box.prepend(Frame(f"{albums} ({num_albums})", label), False, False, 0)

    def _file(self, songs, box):
        length = 0
        size = 0
        for song in songs:
            length += song.get("~#length", 0)
            try:
                size += filesize(song["~filename"])
            except OSError:
                pass
        table = Table(2)
        table.attach(
            Label(_("Total length:")), 0, 1, 0, 1, xoptions=Gtk.AttachOptions.FILL
        )
        table.attach(Label(util.format_time_preferred(length)), 1, 2, 0, 1)
        table.attach(
            Label(_("Total size:")), 0, 1, 1, 2, xoptions=Gtk.AttachOptions.FILL
        )
        table.attach(Label(util.format_size(size)), 1, 2, 1, 2)
        box.prepend(Frame(_("Files"), table), False, False, 0)


class Information(Window, PersistentWindowMixin):
    def __init__(self, library, songs, parent=None):
        super().__init__(dialog=False)
        self.set_default_size(400, 400)
        self.set_transient_for(qltk.get_top_parent(parent))
        self.enable_window_tracking("quodlibet_information")
        if len(songs) > 1:
            connect_destroy(library, "changed", self.__check_changed)
        if len(songs) > 0:
            connect_destroy(library, "removed", self.__check_removed)
        self.__songs = songs
        self.__update(library)
        self.get_child().show_all()

    def __check_changed(self, library, songs):
        changed = set(songs)
        for song in self.__songs:
            if song in changed:
                self.__update(library)
                break

    def __check_removed(self, library, songs):
        gone = set(songs)
        old = len(self.__songs)
        self.__songs = [s for s in self.__songs if s not in gone]
        if len(self.__songs) != old:
            self.__update(library)

    def __update(self, library):
        songs = self.__songs
        if self.get_child():
            self.get_child().destroy()
        self.__songs = songs
        if not songs:
            self.add(NoSongs())
        elif len(songs) == 1:
            self.add(OneSong(library, songs[0]))
        else:
            tags = [(s.get("artist", ""), s.get("album", "")) for s in songs]
            artists, albums = zip(*tags, strict=False)
            if min(albums) == max(albums) and albums[0]:
                self.add(OneAlbum(songs))
            elif min(artists) == max(artists) and artists[0]:
                self.add(OneArtist(songs))
            else:
                self.add(ManySongs(songs))

        self.set_title(self.get_child().title + " - Quod Libet")
        self.get_child().show_all()
