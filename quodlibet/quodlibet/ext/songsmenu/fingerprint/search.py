# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from contextlib import contextmanager

from gi.repository import Gtk, Pango

from .analyze import FingerPrintThreadPool
from .acoustid import AcoustidLookupThread
from quodlibet.qltk.models import ObjectStore
from quodlibet.qltk.views import AllTreeView
from quodlibet.qltk.window import Window
from quodlibet.qltk.x import Button


class Status(object):
    QUEUED = 0
    ANALYZING = 1
    LOOKUP = 2
    DONE = 3
    ERROR = 4

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


class SearchEntry(object):

    def __init__(self, song):
        self.song = song
        self.status = Status.QUEUED
        self.result = None
        self.active_release = 0

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
        super(ResultView, self).__init__()

        render = Gtk.CellRendererText()
        render.set_property('ellipsize', Pango.EllipsizeMode.MIDDLE)
        column = Gtk.TreeViewColumn(_("File"), render)

        def cell_data(column, cell, model, iter_, data):
            entry = model.get_value(iter_)
            cell.set_property('text', entry.song("~basename"))

        column.set_cell_data_func(render, cell_data)
        self.append_column(column)

        render = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Status"), render)

        def cell_data(column, cell, model, iter_, data):
            entry = model.get_value(iter_)
            cell.set_property('text', Status.to_string(entry.status))

        column.set_cell_data_func(render, cell_data)
        self.append_column(column)

        render = Gtk.CellRendererText()
        render.set_property('ellipsize', Pango.EllipsizeMode.END)
        column = Gtk.TreeViewColumn(_("Release ID"), render)

        def cell_data(column, cell, model, iter_, data):
            entry = model.get_value(iter_)
            release = entry.release
            if not release:
                cell.set_property("text", "-")
            else:
                cell.set_property("text", release.id)

        column.set_cell_data_func(render, cell_data)
        self.append_column(column)

class SearchWindow(Window):

    def __init__(self, songs, title=None):
        super(SearchWindow, self).__init__(
            default_width=500, default_height=400, border_width=12,
            title=title)

        self._thread = AcoustidLookupThread(self.__lookup_cb)

        sw = Gtk.ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.IN)

        model = ObjectStore()
        view = ResultView()
        view.set_model(model)
        self.model = model

        self._iter_map = {}
        for song in songs:
            iter_ = self.model.append([SearchEntry(song)])
            self._iter_map[song] = iter_

        sw.add(view)

        self.pool = pool = FingerPrintThreadPool()
        pool.connect('fingerprint-done', self.__fp_done_cb)
        pool.connect('fingerprint-error', self.__fp_error_cb)
        pool.connect('fingerprint-started', self.__fp_started_cb)
        for song in songs:
            pool.push(song)

        outer_box = Gtk.VBox(spacing=12)

        bbox = Gtk.HButtonBox()
        bbox.set_layout(Gtk.ButtonBoxStyle.END)
        bbox.set_spacing(6)
        self.__save = save = Button(_("_Save"), Gtk.STOCK_SAVE)
        save.connect("clicked", self.__on_save)
        save.set_sensitive(False)
        cancel = Gtk.Button(stock=Gtk.STOCK_CANCEL)
        cancel.connect("clicked", lambda *x: self.destroy())
        bbox.pack_start(save, True, True, 0)
        bbox.pack_start(cancel, True, True, 0)

        outer_box.pack_start(sw, True, True, 0)
        outer_box.pack_start(bbox, False, True, 0)

        outer_box.show_all()
        self.add(outer_box)

        self._release_counts = {}
        self.__done = 0

        self.connect("destroy", self.__destroy)

    def __destroy(self, *args):
        self.pool.stop()
        self._thread.stop()

    def __on_save(self, *args):
        for row in self.model:
            entry = row[0]
            if entry.status != Status.DONE or not entry.release:
                continue
            entry.song.update(entry.release.tags)
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

        def sort_key(release):
            # good if there are many other songs that could be in the
            # same release and this release is likely as well.
            # Also sort by id to have a winner in case of a tie.
            return ((self._release_counts[release.id] - release.score) *
                    release.score, release.id)

        for row in self.model:
            entry = row[0]
            if not entry.releases:
                continue
            active_release = entry.active_release
            best_release = sorted(entry.releases, key=sort_key)[-1]
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
                score = release.score
                if id_ in self._release_counts:
                    self._release_counts[id_] += score
                else:
                    self._release_counts[id_] = score

            # update display
            if lresult.releases:
                self.__update_active_releases()

        self.__inc_done()

    def __fp_done_cb(self, pool, result):
        self._thread.put(result)
        with self.__update_row(result.song) as entry:
            entry.status = Status.LOOKUP

    def __fp_error_cb(self, pool, song, error_msg):
        with self.__update_row(song) as entry:
            entry.status = Status.ERROR
        self.__inc_done()

    def __fp_started_cb(self, pool, song):
        with self.__update_row(song) as entry:
            entry.status = Status.ANALYZING
