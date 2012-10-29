# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import time

import gtk
import pango

from quodlibet import const
from quodlibet import qltk
from quodlibet import util

from quodlibet.qltk.bookmarks import EditBookmarksPane
from quodlibet.qltk.cover import CoverImage
from quodlibet.qltk.lyrics import LyricsPane
from quodlibet.qltk.x import Window
from quodlibet.qltk.window import PersistentWindowMixin
from quodlibet.util import tag


def Label(*args):
    l = gtk.Label(*args)
    l.set_selectable(True)
    l.set_alignment(0, 0)
    return l

def Frame(name, widget):
    f = gtk.Frame()
    f.set_shadow_type(gtk.SHADOW_NONE)
    l = gtk.Label()
    l.set_markup("<u><b>%s</b></u>" % name)
    f.set_label_widget(l)
    a = gtk.Alignment(xalign=0, yalign=0, xscale=1, yscale=1)
    a.set_padding(3, 0, 12, 0)
    f.add(a)
    a.add(widget)
    return f

def SW():
    swin = gtk.ScrolledWindow()
    swin.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
    return swin

class ErrorPane(gtk.VBox):
    def __init__(self, song):
        super(ErrorPane, self).__init__(spacing=6)
        self.set_border_width(12)
        sw = gtk.ScrolledWindow()
        view = gtk.TextView()
        view.get_buffer().set_text(song.get("~errors", ""))
        view.set_wrap_mode(gtk.WRAP_WORD)
        sw.add(view)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_IN)
        button = qltk.Button(_("_Clear Errors"), gtk.STOCK_DIALOG_ERROR)
        button.connect('clicked', self.__clear_errors, song, view)
        view.set_editable(False)
        self.pack_start(sw, expand=True, fill=True)
        self.pack_start(button, expand=False, fill=True)

    def __clear_errors(self, button, song, view):
        try: del(song["~errors"])
        except KeyError: pass
        view.get_buffer().set_text("")

class NoSongs(gtk.Label):
    def __init__(self):
        super(NoSongs, self).__init__(_("No songs are selected."))
        self.title = _("No Songs")

class OneSong(qltk.Notebook):
    def __init__(self, library, song):
        super(OneSong, self).__init__()
        vbox = gtk.VBox(spacing=12)
        vbox.set_border_width(12)
        self._title(song, vbox)
        self._album(song, vbox)
        self._people(song, vbox)
        self._library(song, vbox)
        self._file(song, vbox)
        sw = SW()
        sw.title = _("Information")
        sw.add_with_viewport(vbox)
        self.append_page(sw)
        lyrics = LyricsPane(song)
        lyrics.title = _("Lyrics")
        self.append_page(lyrics)

        bookmarks = EditBookmarksPane(None, song)
        bookmarks.title = _("Bookmarks")
        bookmarks.set_border_width(12)
        self.append_page(bookmarks)

        if "~errors" in song:
            errors = ErrorPane(song)
            errors.title = _("Errors")
            self.append_page(errors)

        s = library.connect('changed', self.__check_changed, vbox, song)
        self.connect_object('destroy', library.disconnect, s)

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
            parent = qltk.get_top_parent(self)
            if parent:
                parent.set_title(self.title + " - Quod Libet")
            vbox.show_all()

    def _title(self, song, box):
        l = Label()
        text = "<big><b>%s</b></big>" % util.escape(song.comma("title"))
        if "version" in song:
            text += "\n" + util.escape(song.comma("version"))
        l.set_markup(text)
        l.set_ellipsize(pango.ELLIPSIZE_END)
        box.pack_start(l, expand=False, fill=False)
        self.title = song.comma("title")

    def _album(self, song, box):
        if "album" not in song: return
        w = Label("")
        text = []
        text.append("<i>%s</i>" % util.escape(song.comma("album")))
        if "date" in song:
            text[-1] += " (%s)" % util.escape(song.comma("date"))
        secondary = []
        if "discnumber" in song:
            secondary.append(_("Disc %s") % song["discnumber"])
        if "discsubtitle" in song:
            secondary.append("<i>%s</i>" %
                             util.escape(song.comma("discsubtitle")))
        if "tracknumber" in song:
            secondary.append(_("Track %s") % song["tracknumber"])
        if secondary: text.append(" - ".join(secondary))

        if "organization" in song or "labelid" in song:
            t = util.escape(song.comma("~organization~labelid"))
            text.append(t)

        if "producer" in song:
            text.append("Produced by %s" %(
                util.escape(song.comma("producer"))))

        w.set_markup("\n".join(text))
        w.set_ellipsize(pango.ELLIPSIZE_END)
        hb = gtk.HBox(spacing=12)

        cover = CoverImage(song=song)
        if cover: hb.pack_start(cover, expand=False)
        else: cover.destroy()

        hb.pack_start(w)
        box.pack_start(Frame(tag("album"), hb), expand=False, fill=False)

    def _people(self, song, box):
        vb = gtk.VBox()
        if "artist" in song:
            if len(song.list("artist")) == 1: title = _("artist")
            else: title = _("artists")
            title = util.capitalize(title)
            l = Label(song["artist"])
            l.set_ellipsize(pango.ELLIPSIZE_END)
            vb.pack_start(l, expand=False)
        else:
            title = tag("~people")
        for names, tag_ in [
            ("performers", "performer"),
            ("lyricists", "lyricist"),
            ("arrangers", "arranger"),
            ("composers", "composer"),
            ("conductors", "conductor"),
            ("authors", "author")]:
            if tag_ in song:
                l = Label(song[tag_])
                l.set_ellipsize(pango.ELLIPSIZE_END)
                if len(song.list(tag_)) == 1: name = tag(tag_)
                else: name = _(names)
                vb.pack_start(Frame(util.capitalize(name), l), expand=False)
        performers = {}
        for tag_ in song:
            if "performer:" in tag_:
                for person in song[tag_].split('\n'):
                    try:
                        performers[str(person)]
                    except:
                        performers[str(person)] = []
                    performers[str(person)].append(util.title(tag_[tag_.find(":")+1 : ]))
        if len(performers) > 0:
            performerstr = ''
            for performer in performers:
                performerstr += performer + ' ('
                i = 0
                for part in performers[performer]:
                    if i != 0:
                        performerstr += ', '
                    performerstr += part
                    i += 1
                performerstr += ')\n'
            l = Label(performerstr)
            l.set_ellipsize(pango.ELLIPSIZE_END)
            if len(performers) == 1: name = tag("performer")
            else: name = _("performers")
            vb.pack_start(Frame(util.capitalize(name), l), expand=False)
        if not vb.get_children(): vb.destroy()
        else: box.pack_start(Frame(title, vb), expand=False, fill=False)

    def _library(self, song, box):
        def counter(i):
            if i == 0: return _("Never")
            else: return ngettext("%(n)d time", "%(n)d times", i) % {"n": i}
        def ftime(t):
            if t == 0:
                return _("Unknown")
            else:
                timestr = time.strftime("%c", time.localtime(t))
                return timestr.decode(const.ENCODING)

        playcount = counter(song.get("~#playcount", 0))
        skipcount = counter(song.get("~#skipcount", 0))
        lastplayed = ftime(song.get("~#lastplayed", 0))
        if lastplayed == _("Unknown"):
            lastplayed = _("Never")
        added = ftime(song.get("~#added", 0))
        rating = song("~rating")

        t = gtk.Table(5, 2)
        t.set_col_spacings(6)
        t.set_homogeneous(False)
        table = [(_("added"), added),
                 (_("last played"), lastplayed),
                 (_("plays"), playcount),
                 (_("skips"), skipcount),
                 (_("rating"), rating)]

        for i, (l, r) in enumerate(table):
            l = "<b>%s</b>" % util.capitalize(util.escape(l) + ":")
            lab = Label()
            lab.set_markup(l)
            t.attach(lab, 0, 1, i + 1, i + 2, xoptions=gtk.FILL)
            t.attach(Label(r), 1, 2, i + 1, i + 2)

        box.pack_start(Frame(_("Library"), t), expand=False, fill=False)

    def _file(self, song, box):
        def ftime(t):
            if t == 0:
                return _("Unknown")
            else:
                timestr = time.strftime("%c", time.localtime(t))
                return timestr.decode(const.ENCODING)

        fn = util.fsdecode(util.unexpand(song["~filename"]))
        length = util.format_time_long(song.get("~#length", 0))
        size = util.format_size(
            song.get("~#filesize") or util.size(song["~filename"]))
        mtime = ftime(util.mtime(song["~filename"]))
        bitrate = song.get("~#bitrate", 0)
        if bitrate != 0:
            bitrate = _("%d kbps") % int(bitrate)
        else: bitrate = False

        t = gtk.Table(4, 2)
        t.set_col_spacings(6)
        t.set_homogeneous(False)
        table = [(_("length"), length),
                 (_("file size"), size),
                 (_("modified"), mtime)]
        if bitrate:
            table.insert(1, (_("bitrate"), bitrate))
        fnlab = Label(fn)
        fnlab.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
        t.attach(fnlab, 0, 2, 0, 1, xoptions=gtk.FILL)
        for i, (l, r) in enumerate(table):
            l = "<b>%s</b>" % util.capitalize(util.escape(l) + ":")
            lab = Label()
            lab.set_markup(l)
            t.attach(lab, 0, 1, i + 1, i + 2, xoptions=gtk.FILL)
            t.attach(Label(r), 1, 2, i + 1, i + 2)

        box.pack_start(Frame(_("File"), t), expand=False, fill=False)

class OneAlbum(qltk.Notebook):
    def __init__(self, songs):
        super(OneAlbum, self).__init__()
        swin = SW()
        swin.title = _("Information")
        vbox = gtk.VBox(spacing=12)
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
        l = Label()
        l.set_ellipsize(pango.ELLIPSIZE_END)
        text = "<big><b>%s</b></big>" % util.escape(song["album"])
        if "date" in song: text += "\n" + song["date"]
        l.set_markup(text)
        box.pack_start(l, expand=False, fill=False)
        self.title = song["album"]

    def _album(self, songs, box):
        text = []

        discs = {}
        for song in songs:
            try:
                discs[song("~#disc")] = int(
                    song["tracknumber"].split("/")[1])
            except (AttributeError, ValueError, IndexError, KeyError):
                discs[song("~#disc")] = max([
                    song("~#track", discs.get(song("~#disc"), 0))])
        tracks = sum(discs.values())
        discs = len(discs)
        length = sum([song.get("~#length", 0) for song in songs])

        if tracks == 0 or tracks < len(songs): tracks = len(songs)

        parts = []
        if discs > 1:
            parts.append(
                ngettext("%d disc", "%d discs", discs) % discs)
        parts.append(
                ngettext("%d track", "%d tracks", tracks) % tracks)
        if tracks != len(songs):
            parts.append(ngettext("%d selected", "%d selected",
                len(songs)) % len(songs))

        text.append(", ".join(parts))
        text.append(util.format_time_long(length))

        if "location" in song:
            text.append(util.escape(song["location"]))
        if "organization" in song or "labelid" in song:
            t = util.escape(song.comma("~organization~labelid"))
            text.append(t)

        if "producer" in song:
            text.append(_("Produced by %s") %(
                util.escape(song.comma("producer"))))

        w = Label("")
        w.set_ellipsize(pango.ELLIPSIZE_END)
        w.set_markup("\n".join(text))
        hb = gtk.HBox(spacing=12)

        cover = CoverImage(song=song)
        if cover: hb.pack_start(cover, expand=False)
        else: cover.destroy()

        hb.pack_start(w)
        box.pack_start(hb, expand=False, fill=False)

    def _people(self, songs, box):
        artists = set([])
        performers = set([])
        for song in songs:
            artists.update(song.list("artist"))
            performers.update(song.list("performer"))

        artists = sorted(artists)
        performers = sorted(performers)

        if artists:
            if len(artists) == 1: title = _("artist")
            else: title = _("artists")
            title = util.capitalize(title)
            box.pack_start(Frame(title, Label("\n".join(artists))),
                           expand=False, fill=False)
        if performers:
            if len(artists) == 1: title = _("performer")
            else: title = _("performers")
            title = util.capitalize(title)
            box.pack_start(Frame(title, Label("\n".join(performers))),
                           expand=False, fill=False)

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
                if cur_disc: text.append("")
                cur_track = song("~#track", 1) - 1
                cur_part = None
                cur_disc = disc
                if disc:
                    text.append("<b>%s</b>" % (_("Disc %s") % disc))
            if part != cur_part:
                ts = "    " * bool(disc)
                cur_part = part
                if part:
                    text.append("%s<b>%s</b>" %(ts, util.escape(part)))
            cur_track += 1
            ts = "    " * (bool(disc) + bool(part))
            while cur_track < track:
                text.append("%s<b>%d.</b> <i>%s</i>" %(
                    ts, cur_track, _("Track unavailable")))
                cur_track += 1
            text.append("%s<b>%d.</b> %s" %(
                ts, track, util.escape(song.comma("~title~version"))))
        l = Label()
        l.set_markup("\n".join(text))
        l.set_ellipsize(pango.ELLIPSIZE_END)
        box.pack_start(Frame(_("Track List"), l), expand=False, fill=False)

class OneArtist(qltk.Notebook):
    def __init__(self, songs):
        super(OneArtist, self).__init__()
        swin = SW()
        swin.title = _("Information")
        vbox = gtk.VBox(spacing=12)
        vbox.set_border_width(12)
        swin.add_with_viewport(vbox)
        self._title(songs, vbox)
        self._album(songs, vbox)
        self.append_page(swin)

    def _title(self, songs, box):
        l = Label()
        l.set_ellipsize(pango.ELLIPSIZE_END)
        artist = util.escape(songs[0]("artist"))
        l.set_markup("<b><big>%s</big></b>" % artist)
        box.pack_start(l, expand=False, fill=False)
        self.title = songs[0]["artist"]

    def _album(self, songs, box):
        noalbum = 0
        albums = {}
        for song in songs:
            if "album" in song:
                albums[song.list("album")[0]] = song
            else: noalbum += 1
        albums = [(song.get("date"), song, album) for
                  album, song in albums.items()]
        albums.sort()
        def format((date, song, album)):
            if date: return "%s (%s)" % (album, date[:4])
            else: return album
        covers = [(a, s.find_cover(), s) for d, s, a in albums]
        albums = map(format, albums)
        if noalbum:
            albums.append(ngettext("%d song with no album",
                "%d songs with no album", noalbum) % noalbum)
        l = Label("\n".join(albums))
        l.set_ellipsize(pango.ELLIPSIZE_END)
        box.pack_start(Frame(_("Selected Discography"), l))

        covers = [ac for ac in covers if bool(ac[1])]
        t = gtk.Table(4, (len(covers) // 4) + 1)
        t.set_col_spacings(12)
        t.set_row_spacings(12)
        added = set()
        for i, (album, cover, song) in enumerate(covers):
            if cover.name in added: continue
            cov = CoverImage(song=song)
            cov.child.set_tooltip_text(album)
            c = i % 4
            r = i // 4
            t.attach(cov, c, c + 1, r, r + 1,
                     xoptions=gtk.EXPAND, yoptions=0)
            added.add(cover.name)
        box.pack_start(t)

class ManySongs(qltk.Notebook):
    def __init__(self, songs):
        super(ManySongs, self).__init__()
        swin = SW()
        swin.title = _("Information")
        vbox = gtk.VBox(spacing=12)
        vbox.set_border_width(12)
        swin.add_with_viewport(vbox)
        self._title(songs, vbox)
        self._people(songs, vbox)
        self._album(songs, vbox)
        self._file(songs, vbox)
        self.append_page(swin)

    def _title(self, songs, box):
        l = Label()
        t = ngettext("%d song", "%d songs", len(songs)) % len(songs)
        l.set_markup("<big><b>%s</b></big>" % t)
        self.title = t
        box.pack_start(l, expand=False, fill=False)

    def _people(self, songs, box):
        artists = set([])
        none = 0
        for song in songs:
            if "artist" in song: artists.update(song.list("artist"))
            else: none += 1
        artists = sorted(artists)
        num_artists = len(artists)

        if none: artists.append(ngettext("%d song with no artist",
                "%d songs with no artist", none) % none)
        box.pack_start(Frame(
            "%s (%d)" % (util.capitalize(_("artists")), num_artists),
            Label("\n".join(artists))),
                        expand=False, fill=False)

    def _album(self, songs, box):
        albums = set([])
        none = 0
        for song in songs:
            if "album" in song: albums.update(song.list("album"))
            else: none += 1
        albums = sorted(albums)
        num_albums = len(albums)

        if none: albums.append(ngettext("%d song with no album",
            "%d songs with no album", none) % none)
        box.pack_start(Frame(
            "%s (%d)" % (util.capitalize(_("albums")), num_albums),
            Label("\n".join(albums))),
                        expand=False, fill=False)

    def _file(self, songs, box):
        length = 0
        size = 0
        for song in songs:
            length += song.get("~#length", 0)
            try: size += util.size(song["~filename"])
            except EnvironmentError: pass
        table = gtk.Table(2, 2)
        table.set_col_spacings(6)
        table.attach(Label(_("Total length:")), 0, 1, 0, 1,
                     xoptions=gtk.FILL)
        table.attach(
            Label(util.format_time_long(length)), 1, 2, 0, 1)
        table.attach(Label(_("Total size:")), 0, 1, 1, 2,
                     xoptions=gtk.FILL)
        table.attach(Label(util.format_size(size)), 1, 2, 1, 2)
        box.pack_start(Frame(_("Files"), table),
                       expand=False, fill=False)

class Information(Window, PersistentWindowMixin):
    def __init__(self, library, songs, parent=None):
        super(Information, self).__init__(dialog=False)
        self.set_border_width(12)
        self.set_default_size(400, 400)
        self.enable_window_tracking("quodlibet_information")
        if len(songs) > 1:
            sig = library.connect('changed', self.__check_changed)
            self.connect_object('destroy', library.disconnect, sig)
        if len(songs) > 0:
            sig = library.connect('removed', self.__check_removed)
            self.connect_object('destroy', library.disconnect, sig)
        self.__songs = songs
        self.__update(library)
        self.set_transient_for(qltk.get_top_parent(parent))
        self.show_all()

    def __check_changed(self, library, songs):
        changed = set(songs)
        for song in self.__songs:
            if song in changed:
                self.__update(library)
                break

    def __check_removed(self, library, songs):
        gone = set(songs)
        old = len(self.__songs)
        self.__songs = filter(lambda s: s not in gone, self.__songs)
        if len(self.__songs) != old: self.__update(library)

    def __update(self, library):
        songs = self.__songs
        if self.child: self.child.destroy()
        self.__songs = songs
        if not songs: self.add(NoSongs())
        elif len(songs) == 1: self.add(OneSong(library, songs[0]))
        else:
            tags = [(s.get("artist"), s.get("album")) for s in songs]
            artists, albums = zip(*tags)
            if min(albums) == max(albums) and albums[0]:
                self.add(OneAlbum(songs))
            elif min(artists) == max(artists) and artists[0]:
                self.add(OneArtist(songs))
            else: self.add(ManySongs(songs))

        self.set_title(self.child.title + " - Quod Libet")
        self.child.show_all()
