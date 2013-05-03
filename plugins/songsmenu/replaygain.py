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

from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import Pango
from gi.repository import Gst
from gi.repository import GLib

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


class ReplayGainPipeline(GObject.Object):

    __gsignals__ = {
        # done(self, album)
        'done': (GObject.SignalFlags.RUN_LAST, None, (object,)),
        # update(self, album, song)
        'update': (GObject.SignalFlags.RUN_LAST, None,
                   (object, object,)),
    }

    def __init__(self):
        super(ReplayGainPipeline, self).__init__()

        self._current = None
        self._setup_pipe()

    def _setup_pipe(self):
        # gst pipeline for replay gain analysis:
        # filesrc!decodebin!audioconvert!audioresample!rganalysis!fakesink
        self.pipe = Gst.Pipeline()
        self.filesrc = Gst.ElementFactory.make("filesrc", "source")
        self.pipe.add(self.filesrc)

        self.decode = Gst.ElementFactory.make("decodebin", "decode")

        def new_decoded_pad(dbin, pad):
            pad.link(self.convert.get_static_pad("sink"))

        def removed_decoded_pad(dbin, pad):
            pad.unlink(self.convert.get_static_pad("sink"))

        self.decode.connect("pad-added", new_decoded_pad)
        self.decode.connect("pad-removed", removed_decoded_pad)
        self.pipe.add(self.decode)
        self.filesrc.link(self.decode)

        self.convert = Gst.ElementFactory.make("audioconvert", "convert")
        self.pipe.add(self.convert)

        self.resample = Gst.ElementFactory.make("audioresample", "resample")
        self.pipe.add(self.resample)
        self.convert.link(self.resample)

        self.analysis = Gst.ElementFactory.make("rganalysis", "analysis")
        self.pipe.add(self.analysis)
        self.resample.link(self.analysis)

        self.sink = Gst.ElementFactory.make("fakesink", "sink")
        self.pipe.add(self.sink)
        self.analysis.link(self.sink)

        self.bus = bus = self.pipe.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._bus_message)

    def request_update(self):
        if not self._current:
            return

        ok, p = self.pipe.query_position(Gst.Format.TIME)
        if ok:
            length = self._current.length
            try:
                progress = float(p / Gst.SECOND) / length
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
        self.pipe.set_state(Gst.State.NULL)

    def _next_song(self, first=False):
        if self._current:
            self._current.progress = 1.0
            self._current.done = True
            self._emit_update()
            self._done.append(self._current)
            self._current = None

        if not self._songs:
            self.pipe.set_state(Gst.State.NULL)
            self.emit("done", self._album)
            return

        if first:
            self.analysis.set_property("num-tracks", len(self._songs))
        else:
            self.analysis.set_locked_state(True)
            self.pipe.set_state(Gst.State.NULL)

        self._current = self._songs.pop(0)
        self.filesrc.set_property("location", self._current.filename)
        if not first:
             # flush, so the element takes new data after EOS
            pad = self.analysis.get_static_pad("src")
            pad.send_event(Gst.Event.new_flush_start())
            pad.send_event(Gst.Event.new_flush_stop(True))
            self.analysis.set_locked_state(False)
        self.pipe.set_state(Gst.State.PLAYING)

    def _bus_message(self, bus, message):
        if message.type == Gst.MessageType.TAG:
            tags = message.parse_tag()
            ok, value = tags.get_double(Gst.TAG_TRACK_GAIN)
            if ok:
                self._current.gain = value
            ok, value = tags.get_double(Gst.TAG_TRACK_PEAK)
            if ok:
                self._current.peak = value
            ok, value = tags.get_double(Gst.TAG_ALBUM_GAIN)
            if ok:
                self._album.gain = value
            ok, value = tags.get_double(Gst.TAG_ALBUM_PEAK)
            if ok:
                self._album.peak = value
            self._emit_update()
        elif message.type == Gst.MessageType.EOS:
            self._next_song()
        elif message.type == Gst.MessageType.ERROR:
            gerror, debug = message.parse_error()
            if gerror:
                print_e(gerror.message)
            print_e(debug)
            self._current.error = True
            self._next_song()


class RGDialog(Gtk.Dialog):

    def __init__(self, albums, parent):
        super(RGDialog, self).__init__(
            title=_('ReplayGain Analyzer'), parent=parent,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                     Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        )

        self.set_default_size(500, 350)
        self.set_border_width(6)

        swin = Gtk.ScrolledWindow()
        swin.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        swin.set_shadow_type(Gtk.ShadowType.IN)

        self.vbox.pack_start(swin, True, True, 0)
        view = HintedTreeView()
        swin.add(view)

        def icon_cdf(column, cell, model, iter_, *args):
            item = model[iter_][0]
            if item.error:
                cell.set_property('stock-id', Gtk.STOCK_DIALOG_ERROR)
            else:
                cell.set_property('stock-id', None)

        column = Gtk.TreeViewColumn()
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        icon_render = Gtk.CellRendererPixbuf()
        column.pack_start(icon_render, True)
        column.set_cell_data_func(icon_render, icon_cdf)
        view.append_column(column)

        def track_cdf(column, cell, model, iter_, *args):
            item = model[iter_][0]
            cell.set_property('text', item.title)

        column = Gtk.TreeViewColumn(_("Track"))
        column.set_expand(True)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        track_render = Gtk.CellRendererText()
        track_render.set_property('ellipsize', Pango.EllipsizeMode.END)
        column.pack_start(track_render, True)
        column.set_cell_data_func(track_render, track_cdf)
        view.append_column(column)

        def progress_cdf(column, cell, model, iter_, *args):
            item = model[iter_][0]
            cell.set_property('value', int(item.progress * 100))

        column = Gtk.TreeViewColumn(_("Progress"))
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        progress_render = Gtk.CellRendererProgress()
        column.pack_start(progress_render, True)
        column.set_cell_data_func(progress_render, progress_cdf)
        view.append_column(column)

        def gain_cdf(column, cell, model, iter_, *args):
            item = model[iter_][0]
            if item.gain is None or not item.done:
                cell.set_property('text', "-")
            else:
                cell.set_property('text', "%.2f db" % item.gain)

        column = Gtk.TreeViewColumn(_("Gain"))
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        gain_renderer = Gtk.CellRendererText()
        column.pack_start(gain_renderer, True)
        column.set_cell_data_func(gain_renderer, gain_cdf)
        view.append_column(column)

        def peak_cdf(column, cell, model, iter_, *args):
            item = model[iter_][0]
            if item.gain is None or not item.done:
                cell.set_property('text', "-")
            else:
                cell.set_property('text', "%.2f" % item.peak)

        column = Gtk.TreeViewColumn(_("Peak"))
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        peak_renderer = Gtk.CellRendererText()
        column.pack_start(peak_renderer, True)
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
        self.model = model = Gtk.TreeStore(object)
        insert = model.insert
        for album in reversed(self._todo):
            base = insert(None, 0, row=[album])
            for song in reversed(album.songs):
                insert(base, 0, row=[song])
        view.set_model(model)

        if len(self._todo) == 1:
            view.expand_all()

        self.connect("destroy", self.__destroy)
        self.connect('response', self.__response)

    def start_analysis(self):
        self._timeout = GLib.idle_add(self.__request_update)

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
        if response == Gtk.ResponseType.CANCEL:
            self.destroy()
        elif response == Gtk.ResponseType.OK:
            for album in self._done:
                album.write()
            self.destroy()

    def __destroy(self, *args):
        # shut down any active processing and clean up resources, timeouts
        if self._timeout:
            GLib.source_remove(self._timeout)
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
        GLib.source_remove(self._timeout)
        # all done, stop
        if len(self._done) < self._count:
            for p in self.pipes:
                p.request_update()
            self._timeout = GLib.timeout_add(400, self.__request_update)
        return False


class ReplayGain(SongsMenuPlugin):
    PLUGIN_ID = 'ReplayGain'
    PLUGIN_NAME = 'Replay Gain'
    PLUGIN_DESC = _('Analyzes ReplayGain with gstreamer, grouped by album')
    PLUGIN_ICON = Gtk.STOCK_MEDIA_PLAY

    def plugin_albums(self, albums):
        win = RGDialog(albums, parent=self.plugin_window)
        win.show_all()
        win.start_analysis()

        # plugin_done checks for metadata changes and opens the write dialog
        win.connect("destroy", self.__plugin_done)

    def __plugin_done(self, win):
        self.plugin_finish()


if not Gst.Registry.get().find_plugin("replaygain"):
    __all__ = []
    del ReplayGain
    raise ImportError("GStreamer replaygain plugin not found")
