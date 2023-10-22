# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from contextlib import contextmanager

from gi.repository import Gtk, Pango, Gdk

from .analyze import FingerPrintPool
from .acoustid import AcoustidLookupThread
from .util import get_write_mb_tags, get_group_by_dir
from quodlibet import _
from quodlibet.qltk.models import ObjectStore
from quodlibet.qltk.views import AllTreeView
from quodlibet.qltk.window import Window
from quodlibet.qltk import Button, Icons
from quodlibet import util
from quodlibet.util import print_w
from quodlibet.qltk.ccb import ConfigCheckButton


class Status:
    QUEUED = 0
    ANALYZING = 1
    LOOKUP = 2
    DONE = 3
    ERROR = 4
    UNKNOWN = 5

    @classmethod
    def to_string(cls, value):
        if value == cls.QUEUED:
            return _("Queued")
        elif value == cls.ANALYZING:
            return _("Analyzing")
        elif value == cls.LOOKUP:
            return _("Lookup")
        elif value == cls.DONE:
            return _("Done")
        elif value == cls.ERROR:
            return _("Error")
        elif value == cls.UNKNOWN:
            return _("Unknown")


class SearchEntry:

    def __init__(self, song):
        self.song = song
        self.status = Status.QUEUED
        self.result = None
        self.active_release = 0
        self._write = True

    def toggle_write(self):
        if self.status == Status.DONE and self.release:
            self._write ^= True

    @property
    def can_write(self):
        return self.status == Status.DONE and self.release and self._write

    def apply_tags(self, write_musicbrainz=True, write_album=True):
        """Add the tags of the active release to the song"""

        non_album_tags = [
            "artist",
            "title",
            "musicbrainz_trackid",
            "musicbrainz_artistid"
        ]

        if not self.can_write:
            return

        # To reduce chaotic results with half tagged albums, delete
        # all tags for which we could have written values, but don't
        # or the value would be empty
        for key, value in self.release.tags.items():
            if not write_musicbrainz and key.startswith("musicbrainz_"):
                value = u""
            if not write_album and key not in non_album_tags:
                value = u""

            if not value:
                self.song.pop(key, None)
            else:
                self.song[key] = value

    @property
    def releases(self):
        if self.result:
            return self.result.releases
        return []

    @property
    def release(self):
        result = self.result
        if not result:
            return
        if result.releases:
            return result.releases[self.active_release]


class ResultView(AllTreeView):

    def __init__(self):
        super().__init__()

        self._release_ids = {}

        render = Gtk.CellRendererPixbuf()
        column = Gtk.TreeViewColumn(_("Write"), render)

        def cell_data(column, cell, model, iter_, data):
            entry = model.get_value(iter_)
            cell.set_property("icon-name", Icons.EDIT)
            cell.set_sensitive(entry.can_write)

        column.set_cell_data_func(render, cell_data)
        column.set_expand(False)
        column.set_min_width(60)
        self.append_column(column)

        self.connect("button-press-event", self.__button_press, column)

        render = Gtk.CellRendererText()
        render.set_property("ellipsize", Pango.EllipsizeMode.END)
        column = Gtk.TreeViewColumn(util.tag("~basename"), render)

        def cell_data(column, cell, model, iter_, data):
            entry = model.get_value(iter_)
            cell.set_property("text", entry.song("~basename"))

        column.set_cell_data_func(render, cell_data)
        column.set_expand(True)
        self.append_column(column)

        render = Gtk.CellRendererText()
        render.set_property("ellipsize", Pango.EllipsizeMode.END)
        column = Gtk.TreeViewColumn(_("Status"), render)

        def cell_data(column, cell, model, iter_, data):
            entry = model.get_value(iter_)
            cell.set_property("text", Status.to_string(entry.status))

        column.set_cell_data_func(render, cell_data)
        column.set_expand(False)
        column.set_fixed_width(100)
        self.append_column(column)

        render = Gtk.CellRendererText()
        render.set_property("ellipsize", Pango.EllipsizeMode.END)
        # Translators: album release ID
        column = Gtk.TreeViewColumn(_("Release"), render)
        self._release_column = column

        def cell_data(column, cell, model, iter_, data):
            entry = model.get_value(iter_)
            release = entry.release
            if not release:
                cell.set_property("text", "-")
            else:
                id_ = self.get_release_id(release)
                cell.set_property("text", str(id_))

        column.set_cell_data_func(render, cell_data)
        column.set_expand(False)
        self.append_column(column)

        for tag in ["tracknumber", "artist", "title", "album"]:
            render = Gtk.CellRendererText()
            render.set_property("ellipsize", Pango.EllipsizeMode.END)
            column = Gtk.TreeViewColumn(util.tag(tag), render)

            def cell_data2(column, cell, model, iter_, data, tag=tag):
                entry = model.get_value(iter_)
                release = entry.release
                if not release:
                    cell.set_property("text", "-")
                else:
                    value = release.tags.get(tag, "-")
                    value = ", ".join(value.split("\n"))
                    cell.set_property("text", value)

            column.set_cell_data_func(render, cell_data2)
            self.append_column(column)
            if tag == "tracknumber":
                self._track_column = column
                column.set_expand(False)
                column.set_fixed_width(80)
            else:
                column.set_expand(True)

        for column in self.get_columns():
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            column.set_resizable(True)
            if column.get_min_width() < 50:
                column.set_min_width(50)
        self.set_fixed_height_mode(True)

    def __button_press(self, view, event, edit_column):
        x, y = map(int, [event.x, event.y])
        try:
            path, col, cellx, celly = view.get_path_at_pos(x, y)
        except TypeError:
            return False

        # header clicks go to the first cell otherwise
        if event.window is not view.get_bin_window():
            return False

        if event.button == Gdk.BUTTON_PRIMARY and \
                event.type == Gdk.EventType.BUTTON_PRESS and \
                col == edit_column:
            model = view.get_model()
            row = model[path]
            entry = row[0]
            entry.toggle_write()
            model.row_changed(row.path, row.iter)
            return True

        return False

    def set_album_visible(self, value):
        self._release_column.set_visible(value)
        self._track_column.set_visible(value)

    def get_release_id(self, release):
        return self._release_ids.setdefault(
            release.id, len(self._release_ids) + 1)


def score_release(release):
    return (float(release.sources) / release.all_sources) * release.score


class SearchWindow(Window):

    def __init__(self, songs, title=None):
        super().__init__(
            default_width=800, default_height=400, border_width=12,
            title=title)

        self._thread = AcoustidLookupThread(self.__lookup_cb)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_shadow_type(Gtk.ShadowType.IN)

        model = ObjectStore()
        self.view = view = ResultView()
        view.set_model(model)
        self.model = model

        self._iter_map = {}
        for song in songs:
            iter_ = self.model.append([SearchEntry(song)])
            self._iter_map[song] = iter_

        sw.add(view)

        self.pool = pool = FingerPrintPool()
        pool.connect("fingerprint-done", self.__fp_done_cb)
        pool.connect("fingerprint-error", self.__fp_error_cb)
        pool.connect("fingerprint-started", self.__fp_started_cb)
        for song in songs:
            pool.push(song)

        outer_box = Gtk.VBox(spacing=12)

        bbox = Gtk.HButtonBox()
        bbox.set_layout(Gtk.ButtonBoxStyle.END)
        bbox.set_spacing(6)
        self.__save = save = Button(_("_Save"), Icons.DOCUMENT_SAVE)
        save.connect("clicked", self.__on_save)
        save.set_sensitive(False)
        cancel = Button(_("_Cancel"))
        cancel.connect("clicked", lambda *x: self.destroy())
        bbox.pack_start(save, True, True, 0)
        bbox.pack_start(cancel, True, True, 0)

        inner_box = Gtk.VBox(spacing=6)
        inner_box.pack_start(sw, True, True, 0)

        ccb = ConfigCheckButton(
            _("Write MusicBrainz tags"),
            "plugins", "fingerprint_write_mb_tags")
        ccb.set_active(get_write_mb_tags())
        inner_box.pack_start(ccb, False, True, 0)

        ccb = ConfigCheckButton(
            _("Group by directory"),
            "plugins", "fingerprint_group_by_dir")
        ccb.set_active(get_group_by_dir())
        ccb.connect("toggled", self.__group_toggled)
        self._group_ccb = ccb

        outer_box.pack_start(inner_box, True, True, 0)

        bottom_box = Gtk.HBox(spacing=12)
        mode_button = Gtk.ToggleButton(label=_("Album Mode"))
        mode_button.set_tooltip_text(
            _("Write album related tags and try to "
              "reduce the number of different album releases"))
        mode_button.set_active(True)
        mode_button.connect("toggled", self.__mode_toggle)
        bottom_box.pack_start(mode_button, False, True, 0)
        bottom_box.pack_start(self._group_ccb, False, True, 0)
        bottom_box.pack_start(bbox, True, True, 0)

        outer_box.pack_start(bottom_box, False, True, 0)

        outer_box.show_all()
        self.add(outer_box)

        self.__album_mode = True
        self.__group_by_dir = True
        self._release_scores = {}
        self._directory_scores = {}
        self.__done = 0

        self.connect("destroy", self.__destroy)

    def __group_toggled(self, button):
        self.__group_by_dir = button.get_active()
        self.__update_active_releases()

    def __mode_toggle(self, button):
        self.__album_mode = button.get_active()
        self._group_ccb.set_sensitive(self.__album_mode)
        self.view.set_album_visible(self.__album_mode)
        self.__update_active_releases()

    def __destroy(self, *args):
        self.pool.stop()
        self.pool = None
        self._thread.stop()
        self._thread = None

    def __on_save(self, *args):
        write_mb = get_write_mb_tags()
        write_album = self.__album_mode
        for row in self.model:
            row[0].apply_tags(write_mb, write_album)
            # the plugin wrapper will handle the rest

        self.destroy()

    @contextmanager
    def __update_row(self, song):
        iter_ = self._iter_map[song]
        row = self.model[iter_]
        yield row[0]
        self.model.row_changed(row.path, row.iter)

    def __inc_done(self):
        self.__done += 1
        if self.__done == len(self._iter_map):
            self.__save.set_sensitive(True)

    def __update_active_releases(self):
        """Go through all songs and recalculate the best release"""

        def sort_key(entry, r):
            # good if there are many other songs that could be in the
            # same release and this release is likely as well.
            # Also sort by id to have a winner in case of a tie.
            score = score_release(r)
            if self.__album_mode:
                if self.__group_by_dir:
                    song = entry.song
                    scores = self._directory_scores[song("~dirname")]
                else:
                    scores = self._release_scores
                score = (scores[r.id], score)
            return (score, r.id)

        for row in self.model:
            entry = row[0]
            if not entry.releases:
                continue
            active_release = entry.active_release
            best_release = sorted(
                entry.releases, key=lambda r: sort_key(entry, r))[-1]
            entry.active_release = entry.releases.index(best_release)
            if entry.active_release != active_release:
                self.model.row_changed(row.path, row.iter)

    def __lookup_cb(self, lresult):
        with self.__update_row(lresult.song) as entry:
            entry.status = Status.DONE
            entry.result = lresult

            # count how many times each release ID is present and weight by the
            # score
            for release in lresult.releases:
                id_ = release.id
                # to prevent favoring releases which are a superset of
                # the release we actually want (say 8 CD box containing
                # every song of an artist), try to reduce the medium count.
                score = score_release(release) / release.medium_count
                self._release_scores.setdefault(id_, 0)
                self._release_scores[id_] += score

                # do the same again but group by directory
                dir_ = lresult.song("~dirname")
                release_scores = self._directory_scores.setdefault(dir_, {})
                release_scores.setdefault(id_, 0)
                release_scores[id_] += score

            # update display
            if lresult.releases:
                self.__update_active_releases()
            elif lresult.Error:
                entry.status = Status.ERROR
                # we don't expose in the UI, so at least print it
                print_w(lresult.Error)
            else:
                entry.status = Status.UNKNOWN

        self.__inc_done()

    def __fp_done_cb(self, pool, result):
        self._thread.put(result)
        with self.__update_row(result.song) as entry:
            entry.status = Status.LOOKUP

    def __fp_error_cb(self, pool, song, error_msg):
        print_w(error_msg)
        with self.__update_row(song) as entry:
            entry.status = Status.ERROR
        self.__inc_done()

    def __fp_started_cb(self, pool, song):
        with self.__update_row(song) as entry:
            entry.status = Status.ANALYZING
