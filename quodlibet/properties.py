# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os, sys
import sre
import time
import gtk, pango, gobject

import qltk; from qltk import HintedTreeView, TreeViewHints
import const
import config
import util
import widgets
from gettext import ngettext
from library import library

from widgets import tag

if sys.version_info < (2, 4): from sets import Set as set

VALIDATERS = {
    'date': (sre.compile(r"^\d{4}([-/.]\d{2}([-/.]\d{2}([T ]\d{2}([:.]\d{2}([:.]\d{2})?)?)?)?)?$").match,
            _("The date must be entered in YYYY, YYYY-MM-DD or YYYY-MM-DD HH:MM:SS format.")),

    'replaygain_album_gain': (
    sre.compile(r"^-?\d+\.?\d* dB$").match,
    _("ReplayGain gains must be entered in 'x.yy dB' format.")),

    'replaygain_album_peak': (
    sre.compile(r"^-?\d+\.?\d+?$").match,
    _("ReplayGain peaks must be entered in x.yy format.")),

    }

VALIDATERS["replaygain_track_peak"] = VALIDATERS["replaygain_album_peak"]
VALIDATERS["replaygain_track_gain"] = VALIDATERS["replaygain_album_gain"]

class SongProperties(gtk.Window):
    __gsignals__ = { 'changed': (gobject.SIGNAL_RUN_LAST,
                                 gobject.TYPE_NONE, (object,))
                     }

    class Information(gtk.ScrolledWindow):
        class SongInfo(gtk.VBox):
            def __init__(self, spacing=6, border=12, library=True, songs=[]):
                gtk.VBox.__init__(self, spacing=spacing)
                self.set_border_width(border)
                attrs = ["title", "album", "people", "description", "file"]
                songs = songs[:]
                songs.sort()
                if library: attrs.append("library")
                for attr in attrs:
                    attr = "_" + attr
                    if hasattr(self, attr):
                        getattr(self, attr)(songs)
                self.show_all()

            def Label(self, *args):
                l = gtk.Label(*args)
                l.set_selectable(True)
                l.set_alignment(0, 0)
                return l

            def pack_frame(self, name, widget, expand=False):
                f = gtk.Frame()
                f.set_shadow_type(gtk.SHADOW_NONE)
                l = gtk.Label()
                l.set_markup("<u><b>%s</b></u>" % name)
                f.set_label_widget(l)
                a = gtk.Alignment(xalign=0, yalign=0, xscale=1, yscale=1)
                a.set_padding(3, 0, 12, 0)
                f.add(a)
                a.add(widget)
                self.pack_start(f, expand=expand)

            def _show_big_cover(self, image, event, song):
                if (event.button == 1 and
                    event.type == gtk.gdk._2BUTTON_PRESS):
                    cover = song.find_cover()
                    try: BigCenteredImage(song.comma("album"), cover.name)
                    except: pass

            def _make_cover(self, cover, song):
                p = gtk.gdk.pixbuf_new_from_file_at_size(cover.name, 70, 70)
                i = gtk.Image()
                i.set_from_pixbuf(p)
                ev = gtk.EventBox()
                ev.add(i)
                ev.connect(
                    'button-press-event', self._show_big_cover, song)
                f = gtk.Frame()
                f.set_shadow_type(gtk.SHADOW_ETCHED_OUT)
                f.add(ev)
                return f

        class NoSongs(SongInfo):
            def _description(self, songs):
                self.pack_start(gtk.Label(_("No songs are selected.")))

        class OneSong(SongInfo):
            def _title(self, (song,)):
                l = self.Label()
                text = "<big><b>%s</b></big>" % util.escape(song("title"))
                if "version" in song:
                    text += "\n" + util.escape(song.comma("version"))
                l.set_markup(text)
                l.set_ellipsize(pango.ELLIPSIZE_END)
                self.pack_start(l, expand=False)

            def _album(self, (song,)):
                if "album" not in song: return
                w = self.Label("")
                text = []
                text.append("<i>%s</i>" % util.escape(song.comma("album")))
                if "date" in song:
                    text[-1] += " (%s)" % util.escape(song.comma("date"))
                secondary = []
                if "discnumber" in song:
                    secondary.append(_("Disc %s") % song["discnumber"])
                if "part" in song:
                    secondary.append("<i>%s</i>" %
                                     util.escape(song.comma("part")))
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
                cover = song.find_cover()
                if cover:
                    hb = gtk.HBox(spacing=12)
                    try:
                        hb.pack_start(
                            self._make_cover(cover, song), expand=False)
                    except:
                        hb.destroy()
                        self.pack_frame(tag("album"), w)
                    else:
                        hb.pack_start(w)
                        self.pack_frame(tag("album"), hb)
                else: self.pack_frame(tag("album"), w)

            def _people(self, (song,)):
                vb = SongProperties.Information.SongInfo(3, 0)
                if "artist" in song:
                    title = util.capitalize(ngettext(
                        "artist", "artists", len(song.list('artist'))))
                    l = self.Label(song["artist"])
                    l.set_ellipsize(pango.ELLIPSIZE_END)
                    vb.pack_start(l)
                else:
                    # Translators: This is used as a group header in
                    # Properties when a song has performers/composers/etc.
                    title = _("People")
                for names, tag_ in [
                    ("performers", "performer"),
                    ("lyricists", "lyricist"),
                    ("arrangers", "arranger"),
                    ("composers", "composer"),
                    ("conductors", "conductor"),
                    ("authors", "author")]:
                    if tag_ in song:
                        l = self.Label(song[tag_])
                        l.set_ellipsize(pango.ELLIPSIZE_END)
                        name = ngettext(tag_, names, len(song.list(tag_)))
                        vb.pack_frame(util.capitalize(name), l)
                if not vb.get_children(): vb.destroy()
                else: self.pack_frame(title, vb)

            def _library(self, (song,)):
                def counter(i):
                    if i == 0: return _("Never")
                    else: return ngettext("%d time", "%d times", i) % i
                def ftime(t):
                    if t == 0: return _("Unknown")
                    else: return time.strftime("%c", time.localtime(t))

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
                         (_("play count"), playcount),
                         (_("skip count"), skipcount),
                         (_("rating"), rating)]

                for i, (l, r) in enumerate(table):
                    l = "<b>%s</b>" % util.capitalize(util.escape(l) + ":")
                    lab = self.Label()
                    lab.set_markup(l)
                    t.attach(lab, 0, 1, i + 1, i + 2, xoptions=gtk.FILL)
                    t.attach(self.Label(r), 1, 2, i + 1, i + 2)
                    
                self.pack_frame(_("Library"), t)

            def _file(self, (song,)):
                def ftime(t):
                    if t == 0: return _("Unknown")
                    else: return time.strftime("%c", time.localtime(t))

                fn = util.fsdecode(util.unexpand(song["~filename"]))
                length = util.format_time_long(song["~#length"])
                size = util.format_size(os.path.getsize(song["~filename"]))
                mtime = ftime(util.mtime(song["~filename"]))
                if "~#bitrate" in song and song["~#bitrate"] != 0:
                    bitrate = _("%d kbps") % int(song["~#bitrate"]/1000)
                else: bitrate = False

                t = gtk.Table(4, 2)
                t.set_col_spacings(6)
                t.set_homogeneous(False)
                table = [(_("length"), length),
                         (_("file size"), size),
                         (_("modified"), mtime)]
                if bitrate:
                    table.insert(1, (_("bitrate"), bitrate))
                fnlab = self.Label(fn)
                fnlab.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
                t.attach(fnlab, 0, 2, 0, 1, xoptions=gtk.FILL)
                for i, (l, r) in enumerate(table):
                    l = "<b>%s</b>" % util.capitalize(util.escape(l) + ":")
                    lab = self.Label()
                    lab.set_markup(l)
                    t.attach(lab, 0, 1, i + 1, i + 2, xoptions=gtk.FILL)
                    t.attach(self.Label(r), 1, 2, i + 1, i + 2)
                    
                self.pack_frame(_("File"), t)

        class OneAlbum(SongInfo):
            def _title(self, songs):
                song = songs[0]
                l = self.Label()
                l.set_ellipsize(pango.ELLIPSIZE_END)
                text = "<big><b>%s</b></big>" % util.escape(song["album"])
                if "date" in song: text += "\n" + song["date"]
                l.set_markup(text)
                self.pack_start(l, expand=False)

            def _album(self, songs):
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
                length = sum([song["~#length"] for song in songs])

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

                w = self.Label("")
                w.set_ellipsize(pango.ELLIPSIZE_END)
                w.set_markup("\n".join(text))
                cover = song.find_cover()
                if cover:
                    hb = gtk.HBox(spacing=12)
                    try:
                        hb.pack_start(
                            self._make_cover(cover, song), expand=False)
                    except:
                        hb.destroy()
                        self.pack_start(w, expand=False)
                    else:
                        hb.pack_start(w)
                        self.pack_start(hb, expand=False)
                else: self.pack_start(w, expand=False)

            def _people(self, songs):
                artists = set([])
                performers = set([])
                for song in songs:
                    artists.update(song.list("artist"))
                    performers.update(song.list("performer"))

                artists = list(artists); artists.sort()
                performers = list(performers); performers.sort()

                if artists:
                    title = util.capitalize(
                        ngettext("artist", "artists", len(artists)))
                    self.pack_frame(title, self.Label("\n".join(artists)))
                if performers:
                    title = util.capitalize(
                        ngettext("performer", "performers", len(performers)))
                    if len(performers) == 1: title = tag("performer")
                    else: title = util.capitalize(_("performers"))
                    self.pack_frame(title, self.Label("\n".join(performers)))

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
                l = self.Label()
                l.set_markup("\n".join(text))
                l.set_ellipsize(pango.ELLIPSIZE_END)
                self.pack_frame(_("Track List"), l)

        class OneArtist(SongInfo):
            def _title(self, songs):
                l = self.Label()
                l.set_ellipsize(pango.ELLIPSIZE_END)
                artist = util.escape(songs[0]("artist"))
                l.set_markup("<b><big>%s</big></b>" % artist)
                self.pack_start(l, expand=False)

            def _album(self, songs):
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
                l = self.Label("\n".join(albums))
                l.set_ellipsize(pango.ELLIPSIZE_END)
                self.pack_frame(_("Selected Discography"), l)

                tips = gtk.Tooltips()
                covers = [ac for ac in covers if bool(ac[1])]
                t = gtk.Table(4, (len(covers) // 4) + 1)
                t.set_col_spacings(12)
                t.set_row_spacings(12)
                added = set()
                for i, (album, cover, song) in enumerate(covers):
                    if cover.name in added: continue
                    try:
                        cov = self._make_cover(cover, song)
                        tips.set_tip(cov.child, album)
                        c = i % 4
                        r = i // 4
                        t.attach(cov, c, c + 1, r, r + 1,
                                 xoptions=gtk.EXPAND, yoptions=0)
                    except: pass
                    added.add(cover.name)
                self.pack_start(t, expand=False)
                tips.enable()
                self.connect_object('destroy', gtk.Tooltips.destroy, tips)

        class ManySongs(SongInfo):
            def _title(self, songs):
                l = self.Label()
                t = ngettext("%d song", "%d songs", len(songs)) % len(songs)
                l.set_markup("<big><b>%s</b></big>" % t)
                self.pack_start(l, expand=False)

            def _people(self, songs):
                artists = set([])
                none = 0
                for song in songs:
                    if "artist" in song: artists.update(song.list("artist"))
                    else: none += 1
                artists = list(artists)
                artists.sort()
                num_artists = len(artists)

                if none: artists.append(ngettext("%d song with no artist",
                        "%d songs with no artist", none) % none)
                self.pack_frame(
                    "%s (%d)" % (util.capitalize(_("artists")), num_artists),
                    self.Label("\n".join(artists)))

            def _album(self, songs):
                albums = set([])
                none = 0
                for song in songs:
                    if "album" in song: albums.update(song.list("album"))
                    else: none += 1
                albums = list(albums)
                albums.sort()
                num_albums = len(albums)

                if none: albums.append(ngettext("%d song with no album",
                    "%d songs with no album", none) % none)
                self.pack_frame(
                    "%s (%d)" % (util.capitalize(_("albums")), num_albums),
                    self.Label("\n".join(albums)))

            def _file(self, songs):
                time = 0
                size = 0
                for song in songs:
                    time += song["~#length"]
                    try: size += os.path.getsize(song["~filename"])
                    except EnvironmentError: pass
                table = gtk.Table(2, 2)
                table.set_col_spacings(6)
                table.attach(self.Label(_("Total length:")), 0, 1, 0, 1,
                             xoptions=gtk.FILL)
                table.attach(
                    self.Label(util.format_time_long(time)), 1, 2, 0, 1)
                table.attach(self.Label(_("Total size:")), 0, 1, 1, 2,
                             xoptions=gtk.FILL)
                table.attach(self.Label(util.format_size(size)), 1, 2, 1, 2)
                self.pack_frame(_("Files"), table)

        def __init__(self, parent, library):
            gtk.ScrolledWindow.__init__(self)
            self.title = _("Information")
            self.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
            self.add(gtk.Viewport())
            self.child.set_shadow_type(gtk.SHADOW_NONE)
            parent.connect_object(
                'changed', self.__class__.__update, self, library)

        def __update(self, songs, library):
            if self.child.child: self.child.child.destroy()
            
            if len(songs) == 0: Ctr = self.NoSongs
            elif len(songs) == 1: Ctr = self.OneSong
            else:
                albums = [song.get("album") for song in songs]
                artists = [song.get("artist") for song in songs]
                if min(albums) == max(albums) and None not in albums:
                    Ctr = self.OneAlbum
                elif min(artists) == max(artists) and None not in artists:
                    Ctr = self.OneArtist
                else: Ctr = self.ManySongs
            self.child.add(Ctr(library=library, songs=songs))

    class EditTags(gtk.VBox):
        def __init__(self, parent):
            gtk.VBox.__init__(self, spacing=12)
            self.title = _("Edit Tags")
            self.set_border_width(12)

            model = gtk.ListStore(str, str, bool, bool, bool, str)
            view = HintedTreeView(model)
            selection = view.get_selection()
            render = gtk.CellRendererPixbuf()
            column = gtk.TreeViewColumn(_("Write"), render)

            style = view.get_style()
            pixbufs = [ style.lookup_icon_set(stock)
                        .render_icon(style, gtk.TEXT_DIR_NONE, state,
                            gtk.ICON_SIZE_MENU, view, None)
                        for state in (gtk.STATE_INSENSITIVE, gtk.STATE_NORMAL)
                            for stock in (gtk.STOCK_EDIT, gtk.STOCK_DELETE) ]
            def cdf_write(col, rend, model, iter, (write, delete)):
                row = model[iter]
                if not self.__songinfo.can_change(row[0]):
                    rend.set_property(
                        'stock-id', gtk.STOCK_DIALOG_AUTHENTICATION)
                else:
                    rend.set_property('stock-id', None)
                    rend.set_property(
                        'pixbuf', pixbufs[2*row[write]+row[delete]])
            column.set_cell_data_func(render, cdf_write, (2, 4))
            view.append_column(column)
            view.connect(
                'button-press-event', self.__write_toggle, (column, 2))

            render = gtk.CellRendererText()
            column = gtk.TreeViewColumn(
                _('Tag'), render, text=0, strikethrough=4)
            column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            view.append_column(column)

            render = gtk.CellRendererText()
            render.set_property('ellipsize', pango.ELLIPSIZE_END)
            render.set_property('editable', True)
            render.connect('edited', self.__edit_tag, model, 1)
            render.markup = 1
            column = gtk.TreeViewColumn(
                _('Value'), render, markup=1, editable=3, strikethrough=4)
            column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            view.append_column(column)

            sw = gtk.ScrolledWindow()
            sw.set_shadow_type(gtk.SHADOW_IN)
            sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
            sw.add(view)
            self.pack_start(sw)

            buttonbox = gtk.HBox(spacing=18)
            bbox1 = gtk.HButtonBox()
            bbox1.set_spacing(6)
            bbox1.set_layout(gtk.BUTTONBOX_START)
            add = gtk.Button(stock=gtk.STOCK_ADD)
            add.connect('clicked', self.__add_tag, model)
            remove = gtk.Button(stock=gtk.STOCK_REMOVE)
            remove.connect('clicked', self.__remove_tag, view)
            remove.set_sensitive(False)
            bbox1.pack_start(add)
            bbox1.pack_start(remove)

            bbox2 = gtk.HButtonBox()
            bbox2.set_spacing(6)
            bbox2.set_layout(gtk.BUTTONBOX_END)
            revert = gtk.Button(stock=gtk.STOCK_REVERT_TO_SAVED)
            save = gtk.Button(stock=gtk.STOCK_SAVE)
            revert.set_sensitive(False)
            save.set_sensitive(False)
            bbox2.pack_start(revert)
            bbox2.pack_start(save)

            buttonbox.pack_start(bbox1)
            buttonbox.pack_start(bbox2)

            self.pack_start(buttonbox, expand=False)

            tips = gtk.Tooltips()
            for widget, tip in [
                (view, _("Double-click a tag value to change it, "
                         "right-click for other options")),
                (add, _("Add a new tag")),
                (remove, _("Remove selected tag"))]:
                tips.set_tip(widget, tip)
            tips.enable()

            self.connect_object('destroy', gtk.Tooltips.destroy, tips)

            UPDATE_ARGS = [
                view, buttonbox, model, add, [save, revert, remove]]
            parent.connect_object(
                'changed', self.__class__.__update, self, *UPDATE_ARGS)
            revert.connect_object(
                'clicked', self.__update, None, *UPDATE_ARGS)
            revert.connect_object('clicked', parent.set_pending, None)

            save.connect('clicked', self.__save_files, revert, model, parent)
            save.connect_object('clicked', parent.set_pending, None)
            for sig in ['row-inserted', 'row-deleted', 'row-changed']:
                model.connect(sig, self.__enable_save, [save, revert])
                model.connect_object(sig, parent.set_pending, save)

            view.connect('popup-menu', self.__popup_menu)
            view.connect('button-press-event', self.__button_press)
            selection.connect('changed', self.__tag_select, remove)

        def __enable_save(self, *args):
            buttons = args[-1]
            for b in buttons: b.set_sensitive(True)

        def __popup_menu(self, view):
            path, col = view.get_cursor()
            row = view.get_model()[path]
            self.__show_menu(row, 1, 0, view)

        def __button_press(self, view, event):
            if event.button not in (2, 3): return False
            x, y = map(int, [event.x, event.y])
            try: path, col, cellx, celly = view.get_path_at_pos(x, y)
            except TypeError: return True
            view.grab_focus()
            selection = view.get_selection()
            if not selection.path_is_selected(path):
                view.set_cursor(path, col, 0)
            row = view.get_model()[path]

            if event.button == 2: # middle click paste
                if col != view.get_columns()[2]: return False
                display = gtk.gdk.display_manager_get().get_default_display()
                clipboard = gtk.Clipboard(display, "PRIMARY")
                for rend in col.get_cell_renderers():
                    if rend.get_property('editable'):
                        clipboard.request_text(self.__paste, (rend, path[0]))
                        return True
                else: return False

            elif event.button == 3: # right click menu
                self.__show_menu(row, event.button, event.time, view)
                return True

        def __paste(self, clip, text, (rend, path)):
            if text: rend.emit('edited', path, text.strip())

        def __split_into_list(self, activator, view):
            model, iter = view.get_selection().get_selected()
            row = model[iter]
            spls = config.get("editing", "split_on").split()
            vals = util.split_value(util.unescape(row[1]), spls)
            if vals[0] != util.unescape(row[1]):
                row[1] = util.escape(vals[0])
                row[2] = True
                for val in vals[1:]:
                    self.__add_new_tag(model, row[0], val)

        def __split_title(self, activator, view):
            model, iter = view.get_selection().get_selected()
            row = model[iter]
            spls = config.get("editing", "split_on").split()
            title, versions = util.split_title(util.unescape(row[1]), spls)
            if title != util.unescape(row[1]):
                row[1] = util.escape(title)
                row[2] = True
                for val in versions:
                    self.__add_new_tag(model, "version", val)

        def __split_album(self, activator, view):
            model, iter = view.get_selection().get_selected()
            row = model[iter]
            album, disc = util.split_album(util.unescape(row[1]))
            if album != util.unescape(row[1]):
                row[1] = util.escape(album)
                row[2] = True
                self.__add_new_tag(model, "discnumber", disc)

        def __split_people(self, activator, tag, view):
            model, iter = view.get_selection().get_selected()
            row = model[iter]
            spls = config.get("editing", "split_on").split()
            person, others = util.split_people(util.unescape(row[1]), spls)
            if person != util.unescape(row[1]):
                row[1] = util.escape(person)
                row[2] = True
                for val in others:
                    self.__add_new_tag(model, tag, val)

        def __show_menu(self, row, button, time, view):
            menu = gtk.Menu()        
            spls = config.get("editing", "split_on").split()

            b = gtk.ImageMenuItem(_("Split into _multiple values"))
            b.get_image().set_from_stock(gtk.STOCK_FIND_AND_REPLACE,
                                         gtk.ICON_SIZE_MENU)
            b.set_sensitive(len(util.split_value(row[1], spls)) > 1)
            b.connect('activate', self.__split_into_list, view)
            menu.append(b)
            menu.append(gtk.SeparatorMenuItem())

            if row[0] == "album":
                b = gtk.ImageMenuItem(_("Split disc out of _album"))
                b.get_image().set_from_stock(gtk.STOCK_FIND_AND_REPLACE,
                                             gtk.ICON_SIZE_MENU)
                b.connect('activate', self.__split_album, view)
                b.set_sensitive(util.split_album(row[1])[1] is not None)
                menu.append(b)

            elif row[0] == "title":
                b = gtk.ImageMenuItem(_("Split version out of title"))
                b.get_image().set_from_stock(gtk.STOCK_FIND_AND_REPLACE,
                                             gtk.ICON_SIZE_MENU)
                b.connect('activate', self.__split_title, view)
                b.set_sensitive(util.split_title(row[1], spls)[1] != [])
                menu.append(b)

            elif row[0] == "artist":
                ok = (util.split_people(row[1], spls)[1] != [])

                b = gtk.ImageMenuItem(_("Split arranger out of ar_tist"))
                b.get_image().set_from_stock(gtk.STOCK_FIND_AND_REPLACE,
                                             gtk.ICON_SIZE_MENU)
                b.connect('activate', self.__split_people, "arranger", view)
                b.set_sensitive(ok)
                menu.append(b)

                b = gtk.ImageMenuItem(_("Split _performer out of artist"))
                b.get_image().set_from_stock(gtk.STOCK_FIND_AND_REPLACE,
                                             gtk.ICON_SIZE_MENU)
                b.connect('activate', self.__split_people, "performer", view)
                b.set_sensitive(ok)
                menu.append(b)

            if len(menu.get_children()) > 2:
                menu.append(gtk.SeparatorMenuItem())

            b = gtk.ImageMenuItem(gtk.STOCK_REMOVE, gtk.ICON_SIZE_MENU)
            b.connect('activate', self.__remove_tag, view)
            menu.append(b)

            menu.show_all()
            menu.connect('selection-done', lambda m: m.destroy())
            menu.popup(None, None, None, button, time)

        def __tag_select(self, selection, remove):
            model, iter = selection.get_selected()
            remove.set_sensitive(bool(iter and model[iter][3]))

        def __add_new_tag(self, model, comment, value):
            edited = True
            edit = True
            orig = None
            deleted = False
            iters = []
            def find_same_comments(model, path, iter):
                if model[path][0] == comment: iters.append(iter)
            model.foreach(find_same_comments)
            row = [comment, util.escape(value), edited, edit,deleted, orig]
            if len(iters): model.insert_after(iters[-1], row=row)
            else: model.append(row=row)

        def __add_tag(self, activator, model):
            add = AddTagDialog(
                None, self.__songinfo.can_change(), VALIDATERS)

            while True:
                resp = add.run()
                if resp != gtk.RESPONSE_OK: break
                comment = add.get_tag()
                value = add.get_value()
                if not self.__songinfo.can_change(comment):
                    title = ngettext("Invalid tag", "Invalid tags", 1)
                    msg = ngettext(
                        "Invalid tag <b>%s</b>\n\nThe files currently"
                        " selected do not support editing this tag.",
                        "Invalid tags <b>%s</b>\n\nThe files currently"
                        " selected do not support editing these tags.",
                        1) % util.escape(comment)
                    qltk.ErrorMessage(None, title, msg).run
                else:
                    self.__add_new_tag(model, comment, value)
                    break

            add.destroy()

        def __remove_tag(self, activator, view):
            model, iter = view.get_selection().get_selected()
            row = model[iter]
            if row[0] in self.__songinfo:
                row[2] = True # Edited
                row[4] = True # Deleted
            else:
                model.remove(iter)

        def __save_files(self, save, revert, model, parent):
            updated = {}
            deleted = {}
            added = {}
            def create_property_dict(model, path, iter):
                row = model[iter]
                # Edited, and or and not Deleted
                if row[2] and not row[4]:
                    if row[5] is not None:
                        updated.setdefault(row[0], [])
                        updated[row[0]].append((util.decode(row[1]),
                                                util.decode(row[5])))
                    else:
                        added.setdefault(row[0], [])
                        added[row[0]].append(util.decode(row[1]))
                if row[2] and row[4]:
                    if row[5] is not None:
                        deleted.setdefault(row[0], [])
                        deleted[row[0]].append(util.decode(row[5]))
            model.foreach(create_property_dict)

            win = WritingWindow(parent, len(self.__songs))
            for song in self.__songs:
                if not song.valid() and not qltk.ConfirmAction(
                    None, _("Tag may not be accurate"),
                    _("<b>%s</b> changed while the program was running. "
                      "Saving without refreshing your library may "
                      "overwrite other changes to the song.\n\n"
                      "Save this song anyway?") % util.escape(util.fsdecode(
                    song("~basename")))
                    ).run():
                    break

                changed = False
                for key, values in updated.iteritems():
                    for (new_value, old_value) in values:
                        new_value = util.unescape(new_value)
                        if song.can_change(key):
                            if old_value is None: song.add(key, new_value)
                            else: song.change(key, old_value, new_value)
                            changed = True
                for key, values in added.iteritems():
                    for value in values:
                        value = util.unescape(value)
                        if song.can_change(key):
                            song.add(key, value)
                            changed = True
                for key, values in deleted.iteritems():
                    for value in values:
                        value = util.unescape(value)
                        if song.can_change(key) and key in song:
                            song.remove(key, value)
                            changed = True

                if changed:
                    try: song.write()
                    except:
                        qltk.ErrorMessage(
                            None, _("Unable to save song"),
                            _("Saving <b>%s</b> failed. The file "
                              "may be read-only, corrupted, or you "
                              "do not have permission to edit it.")%(
                            util.escape(util.fsdecode(
                            song('~basename'))))).run()
                        widgets.widgets.watcher.error(song)
                        break
                    widgets.widgets.watcher.changed([song])

                if win.step(): break

            win.destroy()
            widgets.widgets.watcher.refresh()
            for b in [save, revert]: b.set_sensitive(False)

        def __edit_tag(self, renderer, path, new, model, colnum):
            new = ', '.join(new.splitlines())
            row = model[path]
            if (row[0] in VALIDATERS and
                not VALIDATERS[row[0]][0](new)):
                qltk.WarningMessage(
                    None, _("Invalid value"),
                    _("Invalid value") + (": <b>%s</b>\n\n" % new) +
                    VALIDATERS[row[0]][1]).run()
            elif row[colnum].replace('<i>','').replace('</i>','') != new:
                row[colnum] = util.escape(new)
                row[2] = True # Edited
                row[4] = False # not Deleted

        def __write_toggle(self, view, event, (writecol, edited)):
            if event.button != 1: return False
            x, y = map(int, [event.x, event.y])
            try: path, col, cellx, celly = view.get_path_at_pos(x, y)
            except TypeError: return False

            if col is writecol:
                row = view.get_model()[path]
                row[edited] = not row[edited]
                return True

        def __update(self, songs, view, buttonbox, model, add, buttons):
            if songs is None: songs = self.__songs

            from library import AudioFileGroup
            self.__songinfo = songinfo = AudioFileGroup(songs)
            self.__songs = songs
            view.set_model(None)
            model.clear()
            view.set_model(model)

            keys = songinfo.realkeys()
            keys.sort()

            if not config.getboolean("editing", "allcomments"):
                machine_comments = set(['replaygain_album_gain',
                                        'replaygain_album_peak',
                                        'replaygain_track_gain',
                                        'replaygain_track_peak'])
                keys = filter(lambda k: k not in machine_comments, keys)

            # reverse order here so insertion puts them in proper order.
            for comment in ['album', 'artist', 'title']:
                try: keys.remove(comment)
                except ValueError: pass
                else: keys.insert(0, comment)

            for comment in keys:
                orig_value = songinfo[comment].split("\n")
                value = songinfo[comment].safenicestr()
                edited = False
                edit = songinfo.can_change(comment)
                deleted = False
                for i, v in enumerate(value.split("\n")):
                    model.append(row=[comment, v, edited, edit, deleted,
                                      orig_value[i]])

            buttonbox.set_sensitive(bool(songinfo.can_change()))
            for b in buttons: b.set_sensitive(False)
            add.set_sensitive(bool(songs))

    class TagByFilename(gtk.VBox):
        def __init__(self, prop):
            gtk.VBox.__init__(self, spacing=6)
            self.title = _("Tag by Filename")
            self.set_border_width(12)
            hbox = gtk.HBox(spacing=12)

            # Main buttons
            preview = qltk.Button(_("_Preview"), gtk.STOCK_CONVERT)
            save = gtk.Button(stock=gtk.STOCK_SAVE)

            # Text entry and preview button
            combo = qltk.ComboBoxEntrySave(
                const.TBP, const.TBP_EXAMPLES.split("\n"))
            hbox.pack_start(combo)
            entry = combo.child
            hbox.pack_start(preview, expand=False)
            self.pack_start(hbox, expand=False)

            # Header preview display
            view = gtk.TreeView()
            sw = gtk.ScrolledWindow()
            sw.set_shadow_type(gtk.SHADOW_IN)
            sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
            sw.add(view)
            self.pack_start(sw)

            # Options
            vbox = gtk.VBox()
            space = gtk.CheckButton(_("Replace _underscores with spaces"))
            space.set_active(config.state("tbp_space"))
            titlecase = gtk.CheckButton(_("_Title-case resulting values"))
            titlecase.set_active(config.state("titlecase"))
            split = gtk.CheckButton(_("Split into _multiple values"))
            split.set_active(config.state("splitval"))
            addreplace = gtk.combo_box_new_text()
            addreplace.append_text(_("Tags replace existing ones"))
            addreplace.append_text(_("Tags are added to existing ones"))
            addreplace.set_active(config.getint("settings", "addreplace"))
            for i in [space, titlecase, split]:
                vbox.pack_start(i)
            vbox.pack_start(addreplace)
            self.pack_start(vbox, expand=False)

            # Save button
            bbox = gtk.HButtonBox()
            bbox.set_layout(gtk.BUTTONBOX_END)
            bbox.pack_start(save)
            self.pack_start(bbox, expand=False)

            tips = gtk.Tooltips()
            tips.set_tip(
                titlecase,
                _("The first letter of each word will be capitalized"))
            tips.enable()
            self.connect_object('destroy', gtk.Tooltips.destroy, tips)

            # Changing things -> need to preview again
            kw = { "titlecase": titlecase,
                   "splitval": split, "tbp_space": space }
            for i in [space, titlecase, split]:
                i.connect('toggled', self.__changed, preview, save, kw)
            entry.connect('changed', self.__changed, preview, save, kw)

            UPDATE_ARGS = [prop, view, combo, entry, preview, save,
                           space, titlecase, split]

            # Song selection changed, preview clicked
            preview.connect('clicked', self.__preview_tags, *UPDATE_ARGS)
            prop.connect_object(
                'changed', self.__class__.__update, self, *UPDATE_ARGS)

            # Save changes
            save.connect('clicked', self.__save_files, prop, view, entry,
                         addreplace)

        def __update(self, songs, parent, view, combo, entry, preview, save,
                     space, titlecase, split):
            from library import AudioFileGroup
            self.__songs = songs

            songinfo = AudioFileGroup(songs)
            if songs: pattern_text = entry.get_text().decode("utf-8")
            else: pattern_text = ""
            try: pattern = util.PatternFromFile(pattern_text)
            except sre.error:
                qltk.ErrorMessage(
                    parent, _("Invalid pattern"),
                    _("The pattern\n\t<b>%s</b>\nis invalid. "
                      "Possibly it contains the same tag twice or "
                      "it has unbalanced brackets (&lt; / &gt;).")%(
                    util.escape(pattern_text))).run()
                return
            else:
                if pattern_text:
                    combo.prepend_text(pattern_text)
                    combo.write(const.TBP)

            invalid = []

            for header in pattern.headers:
                if not songinfo.can_change(header):
                    invalid.append(header)
            if len(invalid) and songs:
                title = ngettext("Invalid tag", "Invalid tags", len(invalid))
                msg = ngettext(
                        "Invalid tag <b>%s</b>\n\nThe files currently"
                        " selected do not support editing this tag.",
                        "Invalid tags <b>%s</b>\n\nThe files currently"
                        " selected do not support editing these tags.",
                        len(invalid))

                qltk.ErrorMessage(parent, title,
                                  msg % ", ".join(invalid)).run()
                pattern = util.PatternFromFile("")

            view.set_model(None)
            rep = space.get_active()
            title = titlecase.get_active()
            split = split.get_active()
            model = gtk.ListStore(object, str,
                                 *([str] * len(pattern.headers)))
            for col in view.get_columns():
                view.remove_column(col)

            col = gtk.TreeViewColumn(_('File'), gtk.CellRendererText(),
                                     text=1)
            col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            view.append_column(col)
            for i, header in enumerate(pattern.headers):
                render = gtk.CellRendererText()
                render.set_property('editable', True)
                render.connect(
                    'edited', self.__row_edited, model, i + 2, preview)
                col = gtk.TreeViewColumn(header, render, text=i + 2)
                col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
                view.append_column(col)
            spls = config.get("editing", "split_on")

            for song in songs:
                basename = song("~basename")
                basename = basename.decode(util.fscoding(), "replace")
                row = [song, basename]
                match = pattern.match(song)
                for h in pattern.headers:
                    text = match.get(h, '')
                    if rep: text = text.replace("_", " ")
                    if title: text = util.title(text)
                    if split: text = "\n".join(util.split_value(text, spls))
                    row.append(text)
                model.append(row=row)

            # save for last to potentially save time
            if songs: view.set_model(model)
            preview.set_sensitive(False)
            save.set_sensitive(len(pattern.headers) > 0)

        def __save_files(self, save, parent, view, entry, addreplace):
            pattern_text = entry.get_text().decode('utf-8')
            pattern = util.PatternFromFile(pattern_text)
            add = (addreplace.get_active() == 1)
            config.set("settings", "addreplace", str(addreplace.get_active()))
            win = WritingWindow(parent, len(self.__songs))

            def save_song(model, path, iter):
                song = model[path][0]
                row = model[path]
                changed = False
                if not song.valid() and not qltk.ConfirmAction(
                    parent, _("Tag may not be accurate"),
                    _("<b>%s</b> changed while the program was running. "
                      "Saving without refreshing your library may "
                      "overwrite other changes to the song.\n\n"
                      "Save this song anyway?") %(
                    util.escape(util.fsdecode(song("~basename"))))
                    ).run():
                    return True

                for i, h in enumerate(pattern.headers):
                    if row[i + 2]:
                        if not add or h not in song:
                            song[h] = row[i + 2].decode("utf-8")
                            changed = True
                        else:
                            vals = row[i + 2].decode("utf-8")
                            for val in vals.split("\n"):
                                if val not in song.list(h):
                                    song.add(h, val)
                                    changed = True

                if changed:
                    try: song.write()
                    except:
                        qltk.ErrorMessage(
                            parent, _("Unable to edit song"),
                            _("Saving <b>%s</b> failed. The file "
                              "may be read-only, corrupted, or you "
                              "do not have permission to edit it.")%(
                            util.escape(util.fsdecode(song('~basename'))))
                            ).run()
                        widgets.widgets.watcher.error(song)
                        return True
                    widgets.widgets.watcher.changed([song])

                return win.step()
        
            view.get_model().foreach(save_song)
            win.destroy()
            widgets.widgets.watcher.refresh()
            save.set_sensitive(False)

        def __row_edited(self, renderer, path, new, model, colnum, preview):
            row = model[path]
            if row[colnum] != new:
                row[colnum] = new
                preview.set_sensitive(True)

        def __preview_tags(self, activator, *args):
            self.__update(self.__songs, *args)

        def __changed(self, activator, preview, save, kw):
            for key, widget in kw.items():
                config.set("settings", key, str(widget.get_active()))
            preview.set_sensitive(True)
            save.set_sensitive(False)

    class RenameFiles(gtk.VBox):
        def __init__(self, prop):
            gtk.VBox.__init__(self, spacing=6)
            self.title = _("Rename Files")
            self.set_border_width(12)

            # ComboEntry and Preview button
            hbox = gtk.HBox(spacing=12)
            combo = qltk.ComboBoxEntrySave(
                const.NBP, const.NBP_EXAMPLES.split("\n"))
            hbox.pack_start(combo)
            preview = qltk.Button(_("_Preview"), gtk.STOCK_CONVERT)
            hbox.pack_start(preview, expand=False)
            self.pack_start(hbox, expand=False)

            # Tree view in a scrolling window
            model = gtk.ListStore(object, str, str)
            view = gtk.TreeView(model)
            column = gtk.TreeViewColumn(
                _('File'), gtk.CellRendererText(), text=1)
            column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            view.append_column(column)
            render = gtk.CellRendererText()
            render.set_property('editable', True)

            column = gtk.TreeViewColumn(_('New Name'), render, text=2)
            column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            view.append_column(column)
            sw = gtk.ScrolledWindow()
            sw.set_shadow_type(gtk.SHADOW_IN)
            sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
            sw.add(view)
            self.pack_start(sw)

            # Checkboxes
            replace = qltk.ConfigCheckButton(
                _("Replace spaces with _underscores"),
                "rename", "spaces")
            replace.set_active(config.getboolean("rename", "spaces"))
            windows = qltk.ConfigCheckButton(
                _("Replace _Windows-incompatible characters"),
                "rename", "windows")
            windows.set_active(config.getboolean("rename", "windows"))
            ascii = qltk.ConfigCheckButton(
                _("Replace non-_ASCII characters"),
                "rename", "ascii")
            ascii.set_active(config.getboolean("rename", "ascii"))

            vbox = gtk.VBox()
            vbox.pack_start(replace)
            vbox.pack_start(windows)
            vbox.pack_start(ascii)
            self.pack_start(vbox, expand=False)

            # Save button
            save = gtk.Button(stock=gtk.STOCK_SAVE)
            bbox = gtk.HButtonBox()
            bbox.set_layout(gtk.BUTTONBOX_END)
            bbox.pack_start(save)
            self.pack_start(bbox, expand=False)

            # Set tooltips
            tips = gtk.Tooltips()
            for widget, tip in [
                (windows,
                 _("Characters not allowed in Windows filenames "
                   "(\:?;\"<>|) will be replaced by underscores")),
                (ascii,
                 _("Characters outside of the ASCII set (A-Z, a-z, 0-9, "
                   "and punctuation) will be replaced by underscores"))]:
                tips.set_tip(widget, tip)
            tips.enable()
            self.connect_object('destroy', gtk.Tooltips.destroy, tips)

            # Connect callbacks
            preview_args = [combo, prop, model, save, preview,
                            replace, windows, ascii]
            preview.connect('clicked', self.__preview_files, *preview_args)
            prop.connect_object(
                'changed', self.__class__.__update, self, *preview_args)

            for w in [replace, windows, ascii]:
                w.connect('toggled', self.__preview_files, *preview_args)
            changed_args = [save, preview, combo.child]
            combo.child.connect_object(
                'changed', self.__changed, *changed_args)

            save.connect_object(
                'clicked', self.__rename_files, prop, save, model)

            render.connect('edited', self.__row_edited, model, preview, save)

        def __changed(self, save, preview, entry):
            save.set_sensitive(False)
            preview.set_sensitive(bool(entry.get_text()))

        def __row_edited(self, renderer, path, new, model, preview, save):
            row = model[path]
            if row[2] != new:
                row[2] = new
                preview.set_sensitive(True)
                save.set_sensitive(True)

        def __preview_files(self, button, *args):
            self.__update(self.__songs, *args)
            save = args[3]
            save.set_sensitive(True)
            preview = args[4]
            preview.set_sensitive(False)

        def __rename_files(self, parent, save, model):
            win = WritingWindow(parent, len(self.__songs))

            def rename(model, path, iter):
                song = model[path][0]
                oldname = model[path][1]
                newname = model[path][2]
                try:
                    newname = newname.encode(util.fscoding(), "replace")
                    if library: library.rename(song, newname)
                    else: song.rename(newname)
                    widgets.widgets.watcher.changed([song])
                except:
                    qltk.ErrorMessage(
                        win, _("Unable to rename file"),
                        _("Renaming <b>%s</b> to <b>%s</b> failed. "
                          "Possibly the target file already exists, "
                          "or you do not have permission to make the "
                          "new file or remove the old one.") %(
                        util.escape(util.fsdecode(oldname)),
                        util.escape(util.fsdecode(newname)))).run()
                    widgets.widgets.watcher.error(song)
                    return True
                return win.step()
            model.foreach(rename)
            widgets.widgets.watcher.refresh()
            save.set_sensitive(False)
            win.destroy()

        def __update(self, songs, combo, parent, model, save, preview,
                     replace, windows, ascii):
            self.__songs = songs
            model.clear()
            pattern = combo.child.get_text().decode("utf-8")

            underscore = replace.get_active()
            windows = windows.get_active()
            ascii = ascii.get_active()

            try:
                pattern = util.FileFromPattern(pattern)
            except ValueError: 
                qltk.ErrorMessage(
                    parent,
                    _("Path is not absolute"),
                    _("The pattern\n\t<b>%s</b>\ncontains / but "
                      "does not start from root. To avoid misnamed "
                      "folders, root your pattern by starting "
                      "it with / or ~/.")%(
                    util.escape(pattern))).run()
                return
            else:
                if combo.child.get_text():
                    combo.prepend_text(combo.child.get_text())
                    combo.write(const.NBP)

            for song in self.__songs:
                newname = pattern.match(song)
                code = util.fscoding()
                newname = newname.encode(code, "replace").decode(code)
                basename = song("~basename").decode(code, "replace")
                if underscore: newname = newname.replace(" ", "_")
                if windows:
                    for c in '\\:*?;"<>|':
                        newname = newname.replace(c, "_")
                if ascii:
                    newname = "".join(
                        map(lambda c: ((ord(c) < 127 and c) or "_"),
                            newname))
                model.append(row=[song, basename, newname])
            preview.set_sensitive(False)
            save.set_sensitive(bool(combo.child.get_text()))

    class TrackNumbers(gtk.VBox):
        def __init__(self, prop):
            gtk.VBox.__init__(self, spacing=6)
            self.title = _("Track Numbers")
            self.set_border_width(12)
            hbox = gtk.HBox(spacing=18)
            hbox2 = gtk.HBox(spacing=12)

            hbox_start = gtk.HBox(spacing=3)
            label_start = gtk.Label(_("Start fro_m:"))
            label_start.set_use_underline(True)
            spin_start = gtk.SpinButton()
            spin_start.set_range(1, 99)
            spin_start.set_increments(1, 10)
            spin_start.set_value(1)
            label_start.set_mnemonic_widget(spin_start)
            hbox_start.pack_start(label_start)
            hbox_start.pack_start(spin_start)

            hbox_total = gtk.HBox(spacing=3)
            label_total = gtk.Label(_("_Total tracks:"))
            label_total.set_use_underline(True)
            spin_total = gtk.SpinButton()
            spin_total.set_range(0, 99)
            spin_total.set_increments(1, 10)
            label_total.set_mnemonic_widget(spin_total)
            hbox_total.pack_start(label_total)
            hbox_total.pack_start(spin_total)
            preview = qltk.Button(_("_Preview"), gtk.STOCK_CONVERT)

            hbox2.pack_start(hbox_start, expand=True, fill=False)
            hbox2.pack_start(hbox_total, expand=True, fill=False)
            hbox2.pack_start(preview, expand=True, fill=False)

            model = gtk.ListStore(object, str, str)
            view = HintedTreeView(model)

            self.pack_start(hbox2, expand=False)

            render = gtk.CellRendererText()
            column = gtk.TreeViewColumn(_('File'), render, text=1)
            column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            view.append_column(column)
            column = gtk.TreeViewColumn(_('Track'), render, text=2)
            column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            view.append_column(column)
            view.set_reorderable(True)
            w = gtk.ScrolledWindow()
            w.set_shadow_type(gtk.SHADOW_IN)
            w.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
            w.add(view)
            self.pack_start(w)

            bbox = gtk.HButtonBox()
            bbox.set_spacing(12)
            bbox.set_layout(gtk.BUTTONBOX_END)
            save = gtk.Button(stock=gtk.STOCK_SAVE)
            save.connect_object(
                'clicked', self.__save_files, prop, model)
            revert = gtk.Button(stock=gtk.STOCK_REVERT_TO_SAVED)
            revert.connect_object(
                'clicked', self.__revert_files, spin_total, model,
                save, revert)
            bbox.pack_start(revert)
            bbox.pack_start(save)
            self.pack_start(bbox, expand=False)

            preview_args = [spin_start, spin_total, model, save, revert]
            preview.connect('clicked', self.__preview_tracks, *preview_args)
            spin_total.connect(
                'value-changed', self.__preview_tracks, *preview_args)
            spin_start.connect(
                'value-changed', self.__preview_tracks, *preview_args)
            view.connect_object(
                'drag-end', self.__class__.__preview_tracks, self,
                *preview_args)

            prop.connect_object(
                'changed', self.__class__.__update, self,
                spin_total, model, save, revert)

        def __save_files(self, parent, model):
            win = WritingWindow(parent, len(self.__songs))
            def settrack(model, path, iter):
                song = model[iter][0]
                track = model[iter][2]
                if song.get("tracknumber") == track: return win.step()
                if not song.valid() and not qltk.ConfirmAction(
                    win, _("Tag may not be accurate"),
                    _("<b>%s</b> changed while the program was running. "
                      "Saving without refreshing your library may "
                      "overwrite other changes to the song.\n\n"
                      "Save this song anyway?") %(
                    util.escape(util.fsdecode(song("~basename"))))
                    ).run():
                    return True
                song["tracknumber"] = track
                try: song.write()
                except:
                    qltk.ErrorMessage(
                        win, _("Unable to save song"),
                        _("Saving <b>%s</b> failed. The file may be "
                          "read-only, corrupted, or you do not have "
                          "permission to edit it.")%(
                        util.escape(util.fsdecode(song('~basename'))))).run()
                    widgets.widgets.watcher.error(song)
                    return True
                widgets.widgets.watcher.changed([song])
                return win.step()
            model.foreach(settrack)
            widgets.widgets.watcher.refresh()
            win.destroy()

        def __revert_files(self, *args):
            self.__update(self.__songs, *args)

        def __preview_tracks(self, ctx, start, total, model, save, revert):
            start = start.get_value_as_int()
            total = total.get_value_as_int()
            def refill(model, path, iter):
                if total: s = "%d/%d" % (path[0] + start, total)
                else: s = str(path[0] + start)
                model[iter][2] = s
            model.foreach(refill)
            save.set_sensitive(True)
            revert.set_sensitive(True)

        def __update(self, songs, total, model, save, revert):
            songs = songs[:]
            songs.sort(lambda a, b: (cmp(a("~#track"), b("~#track")) or
                                     cmp(a("~basename"), b("~basename")) or
                                     cmp(a, b)))
            self.__songs = songs
            model.clear()
            total.set_value(len(songs))
            for song in songs:
                if not song.can_change("tracknumber"):
                    self.set_sensitive(False)
                    break
            else: self.set_sensitive(True)
            for song in songs:
                basename = util.fsdecode(song("~basename"))
                model.append(row=[song, basename, song("tracknumber")])
            save.set_sensitive(False)
            revert.set_sensitive(False)

    def __init__(self, songs, initial=1):
        gtk.Window.__init__(self)
        self.set_default_size(300, 430)
        icon_theme = gtk.icon_theme_get_default()
        self.set_icon(icon_theme.load_icon(
            const.ICON, 64, gtk.ICON_LOOKUP_USE_BUILTIN))
        notebook = qltk.Notebook()
        pages = [self.Information(self, library=True)]
        pages.extend([Ctr(self) for Ctr in
                      [self.EditTags, self.TagByFilename, self.RenameFiles]])
        if len(songs) > 1:
            pages.append(self.TrackNumbers(self))
        for page in pages: notebook.append_page(page)
        self.set_border_width(12)
        vbox = gtk.VBox(spacing=12)
        vbox.pack_start(notebook)

        fbasemodel = gtk.ListStore(object, str, str, str)
        fmodel = gtk.TreeModelSort(fbasemodel)
        fview = HintedTreeView(fmodel)
        fview.connect('button-press-event', self.__pre_selection_changed)
        selection = fview.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        csig = selection.connect('changed', self.__selection_changed)
        self.__save = None

        if len(songs) > 1:
            render = gtk.CellRendererText()
            expander = gtk.Expander(ngettext("Apply to this _file...",
                    "Apply to these _files...", len(songs)))
            c1 = gtk.TreeViewColumn(_('File'), render, text=1)
            c1.set_sort_column_id(1)
            c1.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            c2 = gtk.TreeViewColumn(_('Path'), render, text=2)
            c2.set_sort_column_id(3)
            c2.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            fview.append_column(c1)
            fview.append_column(c2)
            fview.set_size_request(-1, 130)
            sw = gtk.ScrolledWindow()
            sw.add(fview)
            sw.set_shadow_type(gtk.SHADOW_IN)
            sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
            expander.add(sw)
            expander.set_use_underline(True)
            vbox.pack_start(expander, expand=False)

        for song in songs:
            fbasemodel.append(
                row = [song,
                       util.fsdecode(song("~basename")),
                       util.fsdecode(song("~dirname")),
                       song["~filename"]])

        self.connect_object('changed', SongProperties.__set_title, self)

        selection.select_all()
        self.add(vbox)
        self.connect_object('destroy', fview.set_model, None)
        self.connect_object('destroy', gtk.ListStore.clear, fbasemodel)

        s1 = widgets.widgets.watcher.connect(
            'changed', self.__refresh, fbasemodel, selection)
        s2 = widgets.widgets.watcher.connect(
            'removed', self.__remove, fbasemodel, selection, csig)
        self.connect_object('destroy', widgets.widgets.watcher.disconnect, s1)
        self.connect_object('destroy', widgets.widgets.watcher.disconnect, s2)
        self.connect_object('changed', self.set_pending, None)

        self.emit('changed', songs)
        self.show_all()
        notebook.set_current_page(initial)

    def __remove(self, watcher, songs, model, selection, sig):
        to_remove = []
        def remove(model, path, iter):
            if model[iter][0] in songs: to_remove.append(iter)
            return len(to_remove) == len(songs)
        model.foreach(remove)
        if to_remove:
            selection.handler_block(sig)
            map(model.remove, to_remove)
            selection.handler_unblock(sig)
            self.__refill(model)

    def __set_title(self, songs):
        if songs:
            if len(songs) == 1: title = songs[0].comma("title")
            else: title = _("%(title)s and %(count)d more") % (
                    {'title':songs[0].comma("title"), 'count':len(songs) - 1})
            self.set_title("%s - %s" % (title, _("Properties")))
        else: self.set_title(_("Properties"))

    def __refresh(self, watcher, songs, model, selection):
        self.__refill(model)
        selection.emit('changed')

    def __refill(self, model):
        def refresh(model, iter, path):
            song = model[iter][0]
            model[iter][1] = song("~basename")
            model[iter][2] = song("~dirname")
            model[iter][3] = song["~filename"]
        model.foreach(refresh)

    def set_pending(self, button, *excess):
        self.__save = button

    def __pre_selection_changed(self, view, event):
        if self.__save:
            resp = qltk.CancelRevertSave(self).run()
            if resp == gtk.RESPONSE_YES: self.__save.clicked()
            elif resp == gtk.RESPONSE_NO: return False
            else: return True # cancel or closed

    def __selection_changed(self, selection):
        model = selection.get_tree_view().get_model()
        if model and len(model) == 1: self.emit('changed', [model[(0,)][0]])
        else:
            model, rows = selection.get_selected_rows()
            songs = [model[row][0] for row in rows]
            self.emit('changed', songs)

gobject.type_register(SongProperties)
