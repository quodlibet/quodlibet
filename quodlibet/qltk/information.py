# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2016-2025 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import time
from collections import defaultdict

from gi.repository import Gtk, Pango

from quodlibet.qltk import add_css
from senf import fsn2text

from quodlibet import _, app, ngettext, qltk, util
from quodlibet.formats import PEOPLE
from quodlibet.qltk.cover import CoverImage, get_no_cover_pixbuf
from quodlibet.qltk.window import PersistentWindowMixin, Window
from quodlibet.util import connect_destroy, tag, capitalize
from quodlibet.util.i18n import numeric_phrase
from quodlibet.util.path import filesize, unexpand
from quodlibet.util.tags import readable


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
        qltk.add_css(self, "* {font-size: 36px}")
        if is_markup:
            self.set_markup(text)
        else:
            self.set_text(text)


class ReactiveCoverImage(CoverImage):
    DEFAULT_SIZE = 160

    def __init__(self, resize=False, size=DEFAULT_SIZE, song=None, tooltip=None):
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
    f = Gtk.Frame()
    f.set_label_align(0.01, 0.5)
    qltk.add_css(f, "* {border-radius: 6px; padding: 3px 6px 12px 9px}")
    l = Gtk.Label(label=name)
    qltk.add_css(l, " * {opacity: 0.6; margin: 2px;}")
    f.set_label_widget(l)
    f.add(widget)
    return f


def table_of(data: list[tuple[str, str, bool]]) -> Gtk.Grid:
    g = Gtk.Grid(column_spacing=24, row_spacing=9)
    g.set_row_homogeneous(True)
    for i, (k, v, sensitive) in enumerate(data):
        g.insert_row(i)
        key = Label(capitalize(k), ellipsize=True)
        key.set_selectable(False)
        key.set_sensitive(False)
        g.attach(key, 0, i, 1, 1)
        value = Label(v, ellipsize=True)
        value.set_sensitive(sensitive)
        value.set_selectable(sensitive)
        g.attach(value, 1, i, 1, 1)
    return g


class NoSongs(Gtk.Label):
    def __init__(self):
        super().__init__(label=_("No songs are selected."))
        self.title = _("No Songs")


class OneSong(Gtk.Box):
    def __init__(self, library, song):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._title(song)
        self._album(song)
        self._people(song)
        self._library(song)
        self._file(song)
        self._additional(song)
        self.title = _("Information")

        connect_destroy(library, "changed", self.__check_changed, song)

    def __check_changed(self, library, songs, vbox, song):
        if song in songs:
            for c in vbox.get_children():
                vbox.remove(c)
                c.destroy()
            self._title(song)
            self._album(song)
            self._people(song)
            self._library(song)
            self._file(song)
            self._additional(song)
            parent = qltk.get_top_parent(self)
            if parent:
                parent.set_title(self.title + " - Quod Libet")
            vbox.show_all()

    def _title(self, song):
        text = util.italic(song.comma("title"))
        if "version" in song:
            text += "\n" + util.escape(song.comma("version"))
        self.pack_start(TitleLabel(text, is_markup=True), False, False, 0)
        self.title = song.comma("title")

    def _album(self, song):
        if "album" not in song:
            return
        text = [f"<span size='xx-large'>{util.italic(song.comma('album'))}</span>"]
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
        hb = Gtk.HBox(spacing=12)

        hb.pack_start(w, True, True, 0)
        self.pack_start(Frame(tag("album"), hb), False, False, 0)

        cover = ReactiveCoverImage(song=song)
        hb.pack_start(cover, False, True, 0)

    def _people(self, song):
        data = []
        if "artist" in song:
            title = _("artist") if len(song.list("artist")) == 1 else _("artists")
            title = util.capitalize(title)
            data.append((title, song["artist"], True))
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
                data.append((name, song[tag_], True))
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
            data.append((name, text, True))

        table = table_of(data)
        self.pack_start(Frame(tag("~people"), table), False, False, 0)

    def _library(self, song):
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

        data = [
            (_("added"), added, True),
            (_("last played"), lastplayed, True),
            (_("plays"), playcount, True),
            (_("skips"), skipcount, True),
            (_("rating"), rating, has_rating),
        ]

        t = table_of(data)

        self.pack_start(Frame(_("Library"), t), False, False, 0)

    def _file(self, song):
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
            (_("path"), fn, True),
            (_("length"), length, True),
            (_("format"), format_, True),
            (_("codec"), codec, True),
            (_("encoding"), encoding, True),
            (_("bitrate"), bitrate, True),
            (_("file size"), size, True),
            (_("modified"), mtime, True),
        ]
        t = table_of(table)
        self.pack_start(Frame(_("File"), t), False, False, 0)

    def _additional(self, song):
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

        data = [
            (readable(key, plural=len(markups) > 1), "\n".join(markups), True)
            for (key, markups) in markup_data
        ]
        table = table_of(data)

        self.pack_start(Frame(_("Additional"), table), False, False, 0)


class OneAlbum(Gtk.Box):
    def __init__(self, songs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.title = _("Information")
        # Needed to get proper track/disc/part ordering
        songs = sorted(songs)
        self._title(songs)
        self._album(songs)
        self._people(songs)
        self._description(songs)

    def _title(self, songs):
        song = songs[0]
        self.title = text = song["album"]
        markup = util.italic(text)
        if "date" in song:
            markup += " <small>({})</small>".format(util.escape(song("~year")))
        self.pack_start(TitleLabel(markup, is_markup=True), False, False, 0)

    def _album(self, songs):
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
        hb = Gtk.HBox(spacing=12)
        hb.pack_start(w, True, True, 0)
        hb.pack_start(ReactiveCoverImage(song=song), False, True, 0)
        self.pack_start(Frame(_("Tracks"), hb), False, False, 0)

    def _people(self, songs):
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
                data.append((name, "\n".join(values), True))

        table = table_of(data)
        self.pack_start(Frame(tag("~people"), table), False, False, 0)

    def _description(self, songs):
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
        self.pack_start(Frame(_("Track List"), l), False, False, 0)


class OneArtist(Gtk.Box):
    def __init__(self, songs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.title = _("Information")
        self._title(songs)
        self._album(songs)

    def _title(self, songs):
        self.title = songs[0]("artist")
        l = TitleLabel(self.title)
        self.pack_start(l, False, False, 0)

    def _album(self, songs):
        albums, no_album_count = _sort_albums(songs)

        def format(date, song, album):
            markup = f"<big>{util.italic(album)}</big>"
            return f"{markup} ({date[:4]})" if date else markup

        added = set()
        fb = Gtk.FlowBox(column_spacing=6, row_spacing=6, homogeneous=True)
        qltk.add_css(fb, "flowbox { padding: 0 6px;}")
        fb.set_min_children_per_line(2)
        fb.set_max_children_per_line(6)
        fb.set_selection_mode(Gtk.SelectionMode.NONE)

        size = ReactiveCoverImage.DEFAULT_SIZE
        missing_pb = get_no_cover_pixbuf(size, size)
        get_cover = app.cover_manager.get_cover

        for d, song, album in albums:
            album_title = format(d, song, album)
            box = Gtk.Box(spacing=6, orientation=Gtk.Orientation.VERTICAL)
            box.set_halign(Gtk.Align.CENTER)

            add_css(box, "box { padding: 6px;}")
            box.set_can_focus(False)
            cover = get_cover(song)
            if cover:
                if cover.name in added:
                    continue
                added.add(cover.name)
                widget = ReactiveCoverImage(song=song, tooltip=album)
            else:
                widget = Gtk.Image.new_from_pixbuf(missing_pb)

            box.pack_start(widget, False, False, 0)
            widget.set_halign(Gtk.Align.CENTER)
            widget.set_size_request(size, size)
            label = Gtk.Label(ellipsize=Pango.EllipsizeMode.END)
            label.set_markup(album_title)
            box.pack_start(label, False, False, 0)

            fb.add(box)
        if no_album_count:
            text = (
                ngettext(
                    "%d song with no album", "%d songs with no album", no_album_count
                )
                % no_album_count
            )
            box = Gtk.Box(spacing=6, orientation=Gtk.Orientation.VERTICAL)
            label = Gtk.Label(
                label=text,
                ellipsize=Pango.EllipsizeMode.END,
                justify=Gtk.Justification.CENTER,
            )
            label.set_halign(Gtk.Align.CENTER)
            label.set_valign(Gtk.Align.CENTER)
            box.pack_start(label, True, True, 0)
            fb.add(box)
        self.pack_start(Frame(_("Selected Discography"), fb), False, False, 0)


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


class ManySongs(Gtk.Box):
    def __init__(self, songs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.title = _("Information")
        self._title(songs)
        self._people(songs)
        self._album(songs)
        self._file(songs)

    def _title(self, songs):
        self.title = ngettext("%d song", "%d songs", len(songs)) % len(songs)
        self.pack_start(TitleLabel(self.title), False, False, 0)

    def _people(self, songs):
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
        self.pack_start(frame, False, False, 0)

    def _album(self, songs):
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
        self.pack_start(Frame(f"{albums} ({num_albums})", label), False, False, 0)

    def _file(self, songs):
        length = 0
        size = 0
        for song in songs:
            length += song.get("~#length", 0)
            try:
                size += filesize(song["~filename"])
            except OSError:
                pass
        data = [
            (_("Total length:"), util.format_time_preferred(length), True),
            (_("Total size:"), util.format_size(size), True),
        ]
        table = table_of(data)
        self.pack_start(Frame(_("Files"), table), False, False, 0)


class Information(Window, PersistentWindowMixin):
    def __init__(self, library, songs, parent=None):
        super().__init__(dialog=False)
        self.set_default_size(400, 500)
        self.set_transient_for(qltk.get_top_parent(parent))
        self.enable_window_tracking("quodlibet_information")
        if len(songs) > 1:
            connect_destroy(library, "changed", self.__check_changed)
        if len(songs) > 0:
            connect_destroy(library, "removed", self.__check_removed)
        self.__songs = songs
        self.__update(library)

    def do_focus(self, direction):
        # Override default focus behavior
        # Return True to indicate we handled it
        return True

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
            content = NoSongs()
        elif len(songs) == 1:
            content = OneSong(library, songs[0])
        else:
            tags = [(s.get("artist", ""), s.get("album", "")) for s in songs]
            artists, albums = zip(*tags, strict=False)
            if min(albums) == max(albums) and albums[0]:
                content = OneAlbum(songs)
            elif min(artists) == max(artists) and artists[0]:
                content = OneArtist(songs)
            else:
                content = ManySongs(songs)
        swin = Gtk.ScrolledWindow()

        swin.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        swin.add_with_viewport(content)
        swin.show_all()
        self.add(swin)
        self.set_title(content.title + " - Quod Libet")
