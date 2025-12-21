# Copyright 2005-2010   Joshua Kwan <joshk@triplehelix.org>,
#                       Michael Ball <michael.ball@gmail.com>,
#                       Steven Robertson <steven@strobe.cc>
#                2017   Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk, Pango
from senf import fsn2text

from quodlibet import _
from quodlibet import util
from quodlibet.qltk import Dialog, Icons
from quodlibet.qltk.models import ObjectStore
from quodlibet.qltk.views import HintedTreeView, MultiDragTreeView
from quodlibet.util.i18n import numeric_phrase

from .query import QueryThread
from .util import pconfig
from .mb import search_releases


def get_artist(album):
    """Returns a single artist likely to be the MB AlbumArtist, or None."""

    for tag in ["albumartist", "artist", "performer"]:
        names = set()
        for song in album:
            for single in filter(None, song.get(tag, "").split("\n")):
                names.add(single)
        if len(names) == 1:
            return names.pop()
        if len(names) > 1:
            return None
    return None


def get_trackcount(album):
    """Returns the track count, hammered into submission."""

    parts = []
    for song in album:
        parts.extend(song.get("tracknumber", "0").split("/"))

    max_count = len(album)
    for part in parts:
        try:
            tracks = int(part)
        except ValueError:
            continue
        max_count = max(max_count, tracks)

    return max_count


def build_query(album):
    """Builds an initial mb release search query.

    See: https://musicbrainz.org/doc/Development/XML%20Web%20Service/
        Version%202/Search#Release
    """

    if not album:
        return ""

    alb = '"{}"'.format(album[0].comma("album").replace('"', ""))
    art = get_artist(album)
    if art:
        art_safe = art.replace('"', "")
        alb = f'{alb} AND artist:"{art_safe}"'
    return f"{alb} AND tracks:{get_trackcount(album):d}"


class ResultComboBox(Gtk.ComboBox):
    """Formatted picker for different Result entries."""

    def __init__(self, model):
        super().__init__(model=model)
        render = Gtk.CellRendererText()
        render.set_fixed_height_from_font(2)

        def celldata(layout, cell, model, iter_, data):
            release = model.get_value(iter_)

            extra_info = ", ".join(
                filter(
                    None,
                    [
                        util.escape(release.date),
                        util.escape(release.country),
                        util.escape(release.medium_format),
                        util.escape(release.labelid),
                    ],
                )
            )

            artist_names = [a.name for a in release.artists]
            disc_count = release.disc_count
            track_count = release.track_count

            discs_text = numeric_phrase("%d disc", "%d discs", disc_count)
            tracks_text = numeric_phrase("%d track", "%d tracks", track_count)

            markup = "{}\n{} - {}, {} ({})".format(
                util.bold(release.title),
                util.escape(", ".join(artist_names)),
                util.escape(discs_text),
                util.escape(tracks_text),
                extra_info,
            )
            cell.set_property("markup", markup)

        self.prepend(render, True)
        self.set_cell_data_func(render, celldata, None)


class ResultTreeView(HintedTreeView, MultiDragTreeView):
    """The result treeview"""

    def __init__(self, album):
        self.album = album
        self._release = None
        self.model = ObjectStore()
        self.model.append_many(album)

        super().__init__(self.model)
        self.set_headers_clickable(True)
        self.set_rules_hint(True)
        self.set_reorderable(True)
        self.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)

        mode = Pango.EllipsizeMode
        cols = [
            (_("Filename"), self.__name_datafunc, True, mode.MIDDLE),
            (_("Disc"), self.__disc_datafunc, False, mode.END),
            (_("Track"), self.__track_datafunc, False, mode.END),
            (_("Title"), self.__title_datafunc, True, mode.END),
            (_("Artist"), self.__artist_datafunc, True, mode.END),
        ]

        for title, func, resize, mode in cols:
            render = Gtk.CellRendererText()
            render.set_property("ellipsize", mode)
            col = Gtk.TreeViewColumn(title, render)
            col.set_cell_data_func(render, func)
            col.set_resizable(resize)
            col.set_expand(resize)
            self.append_column(col)

    def iter_tracks(self):
        """Yields tuples of (release, track, song) combinations as they
        are shown in the list.
        """

        tracks = self._tracks
        for idx, (song,) in enumerate(self.model):
            if song is None:
                continue
            if idx >= len(tracks):
                continue
            track = tracks[idx]
            yield (self._release, track, song)

    def update_release(self, full_release):
        """Updates the TreeView, handling results with a different number of
        tracks than the album being tagged.

        Passing in None will reset the list.
        """

        if full_release is not None:
            tracks = full_release.tracks
        else:
            tracks = []

        for _i in range(len(self.model), len(tracks)):
            self.model.append((None,))
        for _i in range(len(self.model), len(tracks), -1):
            if self.model[-1][0] is not None:
                break
            itr = self.model.get_iter_from_string(str(len(self.model) - 1))
            self.model.remove(itr)

        self._release = full_release

        for row in self.model:
            self.model.row_changed(row.path, row.iter)

        # Only show artists if we have any
        has_artists = bool(filter(lambda t: t.artists, tracks))
        col = self.get_column(4)
        col.set_visible(has_artists)

        # Only show discs column if we have more than one disc
        col = self.get_column(1)
        col.set_visible(bool(full_release) and bool(full_release.disc_count > 1))

        self.columns_autosize()

    @property
    def _tracks(self):
        if self._release is None:
            return []
        return self._release.tracks

    def __name_datafunc(self, col, cell, model, itr, data):
        song = model[itr][0]
        if song:
            cell.set_property("text", fsn2text(song("~basename")))
        else:
            cell.set_property("text", "")

    def __track_datafunc(self, col, cell, model, itr, data):
        idx = model.get_path(itr)[0]
        if idx >= len(self._tracks):
            cell.set_property("text", "")
        else:
            cell.set_property("text", self._tracks[idx].tracknumber)

    def __disc_datafunc(self, col, cell, model, itr, data):
        idx = model.get_path(itr)[0]
        if idx >= len(self._tracks):
            cell.set_property("text", "")
        else:
            cell.set_property("text", self._tracks[idx].discnumber)

    def __title_datafunc(self, col, cell, model, itr, data):
        idx = model.get_path(itr)[0]
        if idx >= len(self._tracks):
            cell.set_property("text", "")
        else:
            cell.set_property("text", self._tracks[idx].title)

    def __artist_datafunc(self, col, cell, model, itr, data):
        idx = model.get_path(itr)[0]
        if idx >= len(self._tracks):
            cell.set_property("text", "")
        else:
            names = [a.name for a in self._tracks[idx].artists]
            cell.set_property("text", ", ".join(names))


def build_song_data(release, track):
    """Returns a dict of tags to apply to a song. All the values are unicode.
    If the value is empty it means the tag should be deleted.
    """

    meta = {}

    def join(l):
        return "\n".join(l)

    # track/disc data
    meta["tracknumber"] = "%s/%d" % (track.tracknumber, track.track_count)
    if release.disc_count > 1:
        meta["discnumber"] = "%s/%d" % (track.discnumber, release.disc_count)
    else:
        meta["discnumber"] = ""
    meta["title"] = track.title
    meta["musicbrainz_releasetrackid"] = track.id
    meta["musicbrainz_trackid"] = ""  # we used to write those, so delete

    # disc data
    meta["discsubtitle"] = track.disctitle

    # release data
    meta["album"] = release.title
    meta["date"] = release.date
    meta["musicbrainz_albumid"] = release.id
    meta["labelid"] = release.labelid

    if not release.is_single_artist and not release.is_various_artists:
        artists = release.artists
        meta["albumartist"] = join([a.name for a in artists])
        meta["albumartistsort"] = join([a.sort_name for a in artists])
        meta["musicbrainz_albumartistid"] = join([a.id for a in artists])
    else:
        meta["albumartist"] = ""
        meta["albumartistsort"] = ""
        meta["musicbrainz_albumartistid"] = ""

    meta["artist"] = join([a.name for a in track.artists])
    meta["artistsort"] = join([a.sort_name for a in track.artists])
    meta["musicbrainz_artistid"] = join([a.id for a in track.artists])
    meta["musicbrainz_releasetrackid"] = track.id

    # clean up "redundant" data
    if meta["albumartist"] == meta["albumartistsort"]:
        meta["albumartistsort"] = ""
    if meta["artist"] == meta["artistsort"]:
        meta["artistsort"] = ""

    # finally, as musicbrainzngs returns str values if it's ascii, we force
    # everything to unicode now
    for key, value in meta.items():
        meta[key] = str(value)

    return meta


def apply_options(meta, year_only, albumartist, artistsort, musicbrainz, labelid):
    """Takes the tags extracted from musicbrainz and adjusts them according
    to the user preferences.
    """

    if year_only:
        meta["date"] = meta["date"].split("-", 1)[0]

    if not albumartist:
        meta["albumartist"] = ""

    if not artistsort:
        meta["albumartistsort"] = ""
        meta["artistsort"] = ""

    if not musicbrainz:
        for key in meta:
            if key.startswith("musicbrainz_"):
                meta[key] = ""

    if not labelid:
        meta["labelid"] = ""


def apply_to_song(meta, song):
    """Applies the tags to a AudioFile instance"""

    for key, value in meta.items():
        if not value:
            song.remove(key)
        else:
            assert isinstance(value, str)
            song[key] = value


def sort_key(song):
    """Sort by path so untagged albums have a good start order. Also
    take into account the directory in case it's split in different folders
    by medium.
    """

    return util.human_sort_key(fsn2text(song("~filename")))


class SearchWindow(Dialog):
    def __init__(self, parent, album):
        self.album = album
        self.album.sort(key=sort_key)

        self._resultlist = ObjectStore()
        self._releasecache = {}
        self._qthread = QueryThread()
        self.current_release = None

        super().__init__(_("MusicBrainz lookup"))

        self.add_button(_("_Cancel"), Gtk.ResponseType.REJECT)
        self.add_icon_button(_("_Save"), Icons.DOCUMENT_SAVE, Gtk.ResponseType.ACCEPT)

        self.set_default_size(650, 500)
        self.set_border_width(5)
        self.set_transient_for(parent)

        save_button = self.get_widget_for_response(Gtk.ResponseType.ACCEPT)
        save_button.set_sensitive(False)

        vb = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
        )
        vb.set_spacing(8)

        hb = Gtk.Box()
        hb.set_spacing(8)
        sq = self.search_query = Gtk.Entry()
        sq.connect("activate", self._do_query)

        sq.set_text(build_query(album))

        lbl = Gtk.Label(label=_("_Query:"))
        lbl.set_use_underline(True)
        lbl.set_mnemonic_widget(sq)
        stb = self.search_button = Gtk.Button(_("S_earch"), use_underline=True)
        stb.connect("clicked", self._do_query)
        hb.prepend(lbl, False, True, 0)
        hb.prepend(sq, True, True, 0)
        hb.prepend(stb, False, True, 0)
        vb.prepend(hb, False, True, 0)

        self.result_combo = ResultComboBox(self._resultlist)
        self.result_combo.connect("changed", self._result_changed)
        vb.prepend(self.result_combo, False, True, 0)

        rhb = Gtk.Box()
        rl = Gtk.Label()
        rl.set_markup(_("Results <i>(drag to reorder)</i>"))
        rl.set_alignment(0, 0.5)
        rhb.prepend(rl, False, True, 0)
        rl = self.result_label = Gtk.Label(label="")
        rhb.append(rl, False, True, 0)
        vb.prepend(rhb, False, True, 0)
        sw = Gtk.ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.IN)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.ALWAYS)
        rtv = self.result_treeview = ResultTreeView(self.album)
        rtv.set_border_width(8)
        sw.add(rtv)
        vb.prepend(sw, True, True, 0)

        # TODO: remove deprecated get_action_area
        # https://developer.gnome.org/gtk3/stable/GtkDialog.html#gtk-dialog-get-action-area
        self.get_action_area().set_border_width(4)
        self.get_content_area().prepend(vb, True, True, 0)
        self.connect("response", self._on_response)
        self.connect("destroy", self._on_destroy)

        stb.emit("clicked")
        self.get_child().show_all()

    def _on_destroy(self, *args):
        self._qthread.stop()

    def _on_response(self, widget, response):
        if response != Gtk.ResponseType.ACCEPT:
            self.destroy()
            return

        self._save()

    def _save(self):
        """Writes values to Song objects."""

        year_only = pconfig.getboolean("year_only")
        albumartist = pconfig.getboolean("albumartist")
        artistsort = pconfig.getboolean("artist_sort")
        musicbrainz = pconfig.getboolean("standard")
        labelid = pconfig.getboolean("labelid2")

        for release, track, song in self.result_treeview.iter_tracks():
            meta = build_song_data(release, track)
            apply_options(
                meta, year_only, albumartist, artistsort, musicbrainz, labelid
            )
            apply_to_song(meta, song)

        self.destroy()

    def _do_query(self, *args):
        """Search for album using the query text."""

        query = self.search_query.get_text()

        if not query:
            self.result_label.set_markup(util.bold(_("Please enter a query.")))
            self.search_button.set_sensitive(True)
            return

        self.result_label.set_markup(util.italic(_("Searching…")))

        self._qthread.add(self._process_results, search_releases, query)

    def _process_results(self, results):
        """Called when a query result is returned.

        `results` is None if an error occurred.
        """

        self._resultlist.clear()
        self.search_button.set_sensitive(True)

        if results is None:
            self.result_label.set_text(_("Error encountered. Please retry."))
            self.search_button.set_sensitive(True)
            return

        self._resultlist.append_many(results)

        if len(results) > 0:
            self.result_label.set_markup(util.italic(_("Loading result…")))
            self.result_combo.set_active(0)
        else:
            self.result_label.set_markup(_("No results found."))

    def _result_changed(self, combo):
        """Called when a release is chosen from the result combo."""

        idx = combo.get_active()
        if idx == -1:
            return
        release = self._resultlist[idx][0]

        if release.id in self._releasecache:
            self._update_result(self._releasecache[release.id])
        else:
            self.result_label.set_markup(util.italic(_("Loading result…")))
            self.result_treeview.update_release(None)
            self._qthread.add(self._update_result, release.fetch_full)

    def _update_result(self, full_release):
        """Callback for release detail download from result combo."""

        if full_release is None:
            self.result_label.set_text(_("Error encountered. Please retry."))
            return

        self.result_label.set_text("")
        self._releasecache.setdefault(full_release.id, full_release)

        self.result_treeview.update_release(full_release)
        self.current_release = full_release
        save_button = self.get_widget_for_response(Gtk.ResponseType.ACCEPT)
        save_button.set_sensitive(True)
