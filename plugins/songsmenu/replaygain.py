#! /usr/bin/env python
#
#    ReplayGain Album Analysis using gstreamer rganalysis element
#    Copyright (C) 2005,2007,2009  Michael Urman
#                            2012  Nick Boultbee
#                            2013  Christoph Reiter
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of version 2 of the GNU General Public License as
#    published by the Free Software Foundation.
#

import gtk
import gobject
import pango
import gst

from quodlibet.qltk.views import HintedTreeView
from quodlibet.plugins.songsmenu import SongsMenuPlugin

__all__ = ['ReplayGain']


def get_num_threads():
    # multiprocessing is >= 2.6.
    # Default to 2 threads if cpu_count isn't implemented for the current arch
    # or multiprocessing isn't available
    try:
        import multiprocessing
        threads = multiprocessing.cpu_count()
    except (ImportError, NotImplementedError):
        threads = 2
    return threads


class RGAlbum(object):
    def __init__(self, rg_songs):
        self.songs = rg_songs
        self.gain = None
        self.peak = None

    @property
    def progress(self):
        all_ = 0.0
        done = 0.0
        for song in self.songs:
            all_ += song.length
            done += song.length * song.progress

        try:
            return max(min(done / all_, 1.0), 0.0)
        except ZeroDivisionError:
            return 0.0

    @property
    def done(self):
        for song in self.songs:
            if not song.done:
                return False
        return True

    @property
    def title(self):
        if not self.songs:
            return ""
        return self.songs[0].song.comma('~artist~album')

    @property
    def error(self):
        for song in self.songs:
            if song.error:
                return True
        return False

    def write(self):
        # Don't write incomplete data
        if not self.done:
            return

        for song in self.songs:
            song._write(self.gain, self.peak)

    @classmethod
    def from_songs(self, songs):
        return RGAlbum([RGSong(s) for s in songs])


class RGSong(object):
    def __init__(self, song):
        self.song = song
        self.error = False
        self.gain = None
        self.peak = None
        self.progress = 0.0
        self.done = False

    def _write(self, album_gain, album_peak):
        if self.error or not self.done:
            return
        song = self.song

        if self.gain is not None:
            song['replaygain_track_gain'] = '%.2f dB' % self.gain
        if self.peak is not None:
            song['replaygain_track_peak'] = '%.4f' % self.peak
        if album_gain is not None:
            song['replaygain_album_gain'] = '%.2f dB' % album_gain
        if album_peak is not None:
            song['replaygain_album_peak'] = '%.4f' % album_peak

    @property
    def title(self):
        return self.song('~tracknumber~title~version')

    @property
    def filename(self):
        return self.song("~filename")

    @property
    def length(self):
        return self.song("~#length")


class ReplayGainPipeline(gobject.GObject):

    __gsignals__ = {
        # done(self, album)
        'done': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object,)),
        # update(self, album, song)
        'update': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                   (object, object,)),
    }

    def __init__(self):
        super(ReplayGainPipeline, self).__init__()

        self._current = None
        self._setup_pipe()

    def _setup_pipe(self):
        # gst pipeline for replay gain analysis:
        # filesrc!decodebin!audioconvert!audioresample!rganalysis!fakesink
        self.pipe = gst.Pipeline("pipe")
        self.filesrc = gst.element_factory_make("filesrc", "source")
        self.pipe.add(self.filesrc)

        self.decode = gst.element_factory_make("decodebin", "decode")

        def new_decoded_pad(dbin, pad, is_last):
            pad.link(self.convert.get_pad("sink"))

        def removed_decoded_pad(dbin, pad):
            pad.unlink(self.convert.get_pad("sink"))

        self.decode.connect("new-decoded-pad", new_decoded_pad)
        self.decode.connect("removed-decoded-pad", removed_decoded_pad)
        self.pipe.add(self.decode)
        self.filesrc.link(self.decode)

        self.convert = gst.element_factory_make("audioconvert", "convert")
        self.pipe.add(self.convert)

        self.resample = gst.element_factory_make("audioresample", "resample")
        self.pipe.add(self.resample)
        self.convert.link(self.resample)

        self.analysis = gst.element_factory_make("rganalysis", "analysis")
        self.pipe.add(self.analysis)
        self.resample.link(self.analysis)

        self.sink = gst.element_factory_make("fakesink", "sink")
        self.pipe.add(self.sink)
        self.analysis.link(self.sink)

        self.bus = bus = self.pipe.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._bus_message)

    def request_update(self):
        if not self._current:
            return

        try:
            p = self.pipe.query_position(gst.FORMAT_TIME)[0]
        except gst.QueryError:
            pass
        else:
            length = self._current.length
            try:
                progress = float(p / gst.SECOND) / length
            except ZeroDivisionError:
                progress = 0.0
            progress = max(min(progress, 1.0), 0.0)
            self._current.progress = progress
            self._emit_update()

    def _emit_update(self):
        self.emit("update", self._album, self._current)

    def start(self, album):
        self._album = album
        self._songs = list(album.songs)
        self._done = []
        self._next_song(first=True)

    def quit(self):
        self.bus.remove_signal_watch()
        self.pipe.set_state(gst.STATE_NULL)

    def _next_song(self, first=False):
        if self._current:
            self._current.progress = 1.0
            self._current.done = True
            self._emit_update()
            self._done.append(self._current)
            self._current = None

        if not self._songs:
            self.pipe.set_state(gst.STATE_NULL)
            self.emit("done", self._album)
            return

        if first:
            self.analysis.set_property("num-tracks", len(self._songs))
        else:
            self.analysis.set_locked_state(True)
            self.pipe.set_state(gst.STATE_NULL)

        self._current = self._songs.pop(0)
        self.filesrc.set_property("location", self._current.filename)
        self.pipe.set_state(gst.STATE_PLAYING)
        if not first:
            self.analysis.set_locked_state(False)

    def _bus_message(self, bus, message):
        if message.type == gst.MESSAGE_TAG:
            if message.src == self.analysis:
                tags = message.parse_tag()
                try:
                    self._current.gain = tags[gst.TAG_TRACK_GAIN]
                    self._current.peak = tags[gst.TAG_TRACK_PEAK]
                except KeyError:
                    pass
                try:
                    self._album.gain = tags[gst.TAG_ALBUM_GAIN]
                    self._album.peak = tags[gst.TAG_ALBUM_PEAK]
                except KeyError:
                    pass
                self._emit_update()
        elif message.type == gst.MESSAGE_EOS:
            self._next_song()
        elif message.type == gst.MESSAGE_ERROR:
            gerror, debug = message.parse_error()
            if gerror:
                print_e(gerror.message)
            print_e(debug)
            self._current.error = True
            self._next_song()


class RGDialog(gtk.Dialog):

    def __init__(self, albums, parent):
        super(RGDialog, self).__init__(
            title=_('ReplayGain Analyzer'), parent=parent,
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                     gtk.STOCK_SAVE, gtk.RESPONSE_OK)
        )

        self.set_default_size(500, 350)
        self.set_border_width(6)

        swin = gtk.ScrolledWindow()
        swin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        swin.set_shadow_type(gtk.SHADOW_IN)

        self.vbox.pack_start(swin)
        view = HintedTreeView()
        swin.add(view)

        def icon_cdf(column, cell, model, iter_):
            item = model[iter_][0]
            if item.error:
                cell.set_property('stock-id', gtk.STOCK_DIALOG_ERROR)
            else:
                cell.set_property('stock-id', None)

        column = gtk.TreeViewColumn()
        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        icon_render = gtk.CellRendererPixbuf()
        column.pack_start(icon_render)
        column.set_cell_data_func(icon_render, icon_cdf)
        view.append_column(column)

        def track_cdf(column, cell, model, iter_):
            item = model[iter_][0]
            cell.set_property('text', item.title)

        column = gtk.TreeViewColumn(_("Track"))
        column.set_expand(True)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        track_render = gtk.CellRendererText()
        track_render.set_property('ellipsize', pango.ELLIPSIZE_END)
        column.pack_start(track_render)
        column.set_cell_data_func(track_render, track_cdf)
        view.append_column(column)

        def progress_cdf(column, cell, model, iter_):
            item = model[iter_][0]
            cell.set_property('value', int(item.progress * 100))

        column = gtk.TreeViewColumn(_("Progress"))
        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        progress_render = gtk.CellRendererProgress()
        column.pack_start(progress_render)
        column.set_cell_data_func(progress_render, progress_cdf)
        view.append_column(column)

        def gain_cdf(column, cell, model, iter_):
            item = model[iter_][0]
            if item.gain is None:
                cell.set_property('text', "-")
            else:
                cell.set_property('text', "%.2f db" % item.gain)

        column = gtk.TreeViewColumn(_("Gain"))
        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        gain_renderer = gtk.CellRendererText()
        column.pack_start(gain_renderer)
        column.set_cell_data_func(gain_renderer, gain_cdf)
        view.append_column(column)

        def peak_cdf(column, cell, model, iter_):
            item = model[iter_][0]
            if item.gain is None:
                cell.set_property('text', "-")
            else:
                cell.set_property('text', "%.2f" % item.peak)

        column = gtk.TreeViewColumn(_("Peak"))
        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        peak_renderer = gtk.CellRendererText()
        column.pack_start(peak_renderer)
        column.set_cell_data_func(peak_renderer, peak_cdf)
        view.append_column(column)

        # create as many pipelines as threads
        self.pipes = []
        for i in xrange(get_num_threads()):
            self.pipes.append(ReplayGainPipeline())

        self._timeout = None
        self._sigs = {}
        self._done = []
        self._todo = list([RGAlbum.from_songs(a) for a in albums])
        self._count = len(self._todo)

        # fill the view
        self.model = model = gtk.TreeStore(object)
        insert = model.insert
        for album in reversed(self._todo):
            base = insert(None, 0, row=[album])
            for song in reversed(album.songs):
                insert(base, 0, row=[song])
        view.set_model(model)

        if len(albums) == 1:
            view.expand_all()

        self.connect("destroy", self.__destroy)
        self.connect('response', self.__response)

    def start_analysis(self):
        self._timeout = gobject.idle_add(self.__request_update)

        # fill the pipelines
        for p in self.pipes:
            if not self._todo:
                break
            self._sigs[p] = [
                p.connect("done", self.__done),
                p.connect("update", self.__update),
            ]
            p.start(self._todo.pop(0))

    def __response(self, win, response):
        if response == gtk.RESPONSE_CANCEL:
            self.destroy()
        elif response == gtk.RESPONSE_OK:
            for album in self._done:
                album.write()
            self.destroy()

    def __destroy(self, *args):
        # shut down any active processing and clean up resources, timeouts
        if self._timeout:
            gobject.source_remove(self._timeout)
        for p in self.pipes:
            if p in self._sigs:
                for s in self._sigs.get(p, []):
                    p.disconnect(s)
            p.quit()

    def __update(self, pipeline, album, song):
        for row in self.model:
            row_album = row[0]
            if row_album is album:
                self.model.row_changed(row.path, row.iter)
                for child in row.iterchildren():
                    row_song = child[0]
                    if row_song is song:
                        self.model.row_changed(child.path, child.iter)
                        break
                break

    def __done(self, pipeline, album):
        self._done.append(album)
        if self._todo:
            pipeline.start(self._todo.pop(0))

        for row in self.model:
            row_album = row[0]
            if row_album is album:
                self.model.row_changed(row.path, row.iter)
                break

    def __request_update(self):
        gobject.source_remove(self._timeout)
        # all done, stop
        if len(self._done) < self._count:
            for p in self.pipes:
                p.request_update()
            self._timeout = gobject.timeout_add(400, self.__request_update)
        return False


class ReplayGain(SongsMenuPlugin):
    PLUGIN_ID = 'ReplayGain'
    PLUGIN_NAME = 'Replay Gain'
    PLUGIN_DESC = _('Analyzes ReplayGain with gstreamer, grouped by album')
    PLUGIN_ICON = gtk.STOCK_MEDIA_PLAY

    def plugin_albums(self, albums):
        win = RGDialog(albums, parent=self.plugin_window)
        win.show_all()
        win.start_analysis()

        # plugin_done checks for metadata changes and opens the write dialog
        win.connect("destroy", self.__plugin_done)

    def __plugin_done(self, win):
        self.plugin_finish()


if not gst.registry_get_default().find_plugin("replaygain"):
    __all__ = []
    del ReplayGain
    raise gst.PluginNotFoundError("replaygain")
