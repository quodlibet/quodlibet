#    ReplayGain Album Analysis using gstreamer rganalysis element
#    Copyright (C) 2005,2007,2009 Michael Urman
#                       2012-2025 Nick Boultbee
#                            2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import Pango
from gi.repository import Gst
from gi.repository import GLib

from quodlibet import print_d, ngettext, C_, _, util
from quodlibet.plugins import PluginConfigMixin, MissingGstreamerElementPluginError

from quodlibet.browsers.collection.models import EMPTY

from quodlibet.qltk.views import HintedTreeView
from quodlibet.qltk.x import Frame
from quodlibet.qltk import Icons, Dialog
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.plugins.songshelpers import is_writable, is_finite, each_song
from quodlibet.util import cached_property, print_w, print_e, format_int_locale
from quodlibet.util.path import uri2gsturi

__all__ = ["ReplayGain"]


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


class UpdateMode:
    """Enum-like class for update strategies"""

    ALWAYS = "always"
    ALBUM_MISSING = "album_tags_missing"
    ANY_MISSING = "any_tags_missing"


class RGAlbum:
    def __init__(self, rg_songs, process_mode):
        self.songs = rg_songs
        self.gain = None
        self.peak = None
        self.__should_process = None
        self.__process_mode = process_mode

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
        # It's ok - any() + generator is short-cut-logic-friendly
        if not any(rgs.song("album") for rgs in self.songs):
            return f"({EMPTY})"
        return self.songs[0].song.comma("~artist~album")

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
    def from_songs(cls, songs, process_mode=UpdateMode.ALWAYS):
        return RGAlbum([RGSong(s) for s in songs], process_mode)

    @cached_property
    def should_process(self):
        """Returns true if the album needs analysis, according to prefs"""
        mode = self.__process_mode
        if mode == UpdateMode.ALWAYS:
            return True
        if mode == UpdateMode.ANY_MISSING:
            return not all(s.has_all_rg_tags for s in self.songs)
        if mode == UpdateMode.ALBUM_MISSING:
            return not all(s.album_gain for s in self.songs)
        print_w("Invalid setting for update mode: " + mode)
        # Safest to re-process probably.
        return True


class RGSong:
    def __init__(self, song):
        self.song = song
        self.error = False
        self.gain = None
        self.peak = None
        self.progress = 0.0
        self.done = False
        # TODO: support prefs for not overwriting individual existing tags
        #       e.g. to re-run over entire library but keeping files untouched
        self.overwrite_existing = True

    def _write(self, album_gain, album_peak):
        if self.error or not self.done:
            return
        song = self.song

        def write_to_song(tag, pattern, value):
            if value is None or value == "":
                return
            existing = song(tag, None)
            if existing and not self.overwrite_existing:
                fn = self.song("~filename")
                print_d(f"Not overwriting existing tag {tag} (={existing}) for {fn}")
                return
            song[tag] = pattern % value

        write_to_song("replaygain_track_gain", "%.2f dB", self.gain)
        write_to_song("replaygain_track_peak", "%.4f", self.peak)
        write_to_song("replaygain_album_gain", "%.2f dB", album_gain)
        write_to_song("replaygain_album_peak", "%.4f", album_peak)

        # bs1770gain writes those and since we still do old replaygain
        # just delete them so players use the defaults.
        song.pop("replaygain_reference_loudness", None)
        song.pop("replaygain_algorithm", None)
        song.pop("replaygain_album_range", None)
        song.pop("replaygain_track_range", None)

    @property
    def title(self):
        return self.song("~tracknumber~title~version")

    @property
    def filename(self):
        return self.song("~filename")

    @property
    def uri(self):
        return self.song("~uri")

    @property
    def length(self):
        return self.song("~#length")

    def _get_rg_tag(self, suffix):
        ret = self.song(f"~#replaygain_{suffix}")
        return None if ret == "" else ret

    @property
    def track_gain(self):
        return self._get_rg_tag("track_gain")

    @property
    def album_gain(self):
        return self._get_rg_tag("album_gain")

    @property
    def track_peak(self):
        return self._get_rg_tag("track_peak")

    @property
    def album_peak(self):
        return self._get_rg_tag("album_peak")

    @property
    def has_track_tags(self):
        return not (self.track_gain is None or self.track_peak is None)

    @property
    def has_album_tags(self):
        return not (self.album_gain is None or self.album_peak is None)

    @property
    def has_all_rg_tags(self):
        return self.has_track_tags and self.has_album_tags

    def __str__(self):
        vals = {
            k: self._get_rg_tag(k)
            for k in "track_gain album_gain album_peak track_peak".split()
        }
        return f"<Song={self.song} RG data={vals}>"


class ReplayGainPipeline(GObject.Object):
    __gsignals__ = {
        # For done(self, album)
        "done": (GObject.SignalFlags.RUN_LAST, None, (object,)),
        # For update(self, album, song)
        "update": (
            GObject.SignalFlags.RUN_LAST,
            None,
            (
                object,
                object,
            ),
        ),
    }

    def __init__(self):
        super().__init__()

        self._current = None
        self._setup_pipe()

    def _setup_pipe(self):
        # gst pipeline for replay gain analysis:
        # uridecodebin!audioconvert!audioresample!rganalysis!fakesink
        self.pipe = Gst.Pipeline()
        self.decode = Gst.ElementFactory.make("uridecodebin", "decode")

        def new_decoded_pad(dbin, pad):
            pad.link(self.convert.get_static_pad("sink"))

        self.decode.connect("pad-added", new_decoded_pad)
        self.pipe.add(self.decode)

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
        self.decode.set_property("uri", uri2gsturi(self._current.uri))
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


class RGDialog(Dialog):
    def __init__(self, albums, parent, process_mode):
        super().__init__(title=_("ReplayGain Analyzer"), parent=parent)

        self.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        self.add_icon_button(_("_Save"), Icons.DOCUMENT_SAVE, Gtk.ResponseType.OK)

        self.process_mode = process_mode
        self.set_default_size(600, 400)
        self.set_border_width(6)

        hbox = Gtk.Box(spacing=6)
        info = Gtk.Label()
        hbox.prepend(info, True, True, 0)
        self.vbox.prepend(hbox, False, False, 6)

        swin = Gtk.ScrolledWindow()
        swin.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        swin.set_shadow_type(Gtk.ShadowType.IN)

        self.vbox.prepend(swin, True, True, 0)
        view = HintedTreeView()
        swin.add(view)

        def icon_cdf(column, cell, model, iter_, *args):
            item = model[iter_][0]
            if item.error:
                cell.set_property("icon-name", Icons.DIALOG_ERROR)
            else:
                cell.set_property("icon-name", Icons.NONE)

        column = Gtk.TreeViewColumn()
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        icon_render = Gtk.CellRendererPixbuf()
        column.prepend(icon_render, True)
        column.set_cell_data_func(icon_render, icon_cdf)
        view.append_column(column)

        def track_cdf(column, cell, model, iter_, *args):
            item = model[iter_][0]
            cell.set_property("text", item.title)
            cell.set_sensitive(model[iter_][1])

        # Translators: Combined track number/title column heading
        column = Gtk.TreeViewColumn(C_("track/title", "Track"))
        column.set_expand(True)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        track_render = Gtk.CellRendererText()
        track_render.set_property("ellipsize", Pango.EllipsizeMode.END)
        column.prepend(track_render, True)
        column.set_cell_data_func(track_render, track_cdf)
        view.append_column(column)

        def progress_cdf(column, cell, model, iter_, *args):
            item = model[iter_][0]
            cell.set_property("value", int(item.progress * 100))
            cell.set_sensitive(model[iter_][1])

        column = Gtk.TreeViewColumn(_("Progress"))
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        progress_render = Gtk.CellRendererProgress()
        column.prepend(progress_render, True)
        column.set_cell_data_func(progress_render, progress_cdf)
        view.append_column(column)

        def gain_cdf(column, cell, model, iter_, *args):
            item = model[iter_][0]
            if item.gain is None or not item.done:
                cell.set_property("text", "-")
            else:
                cell.set_property("text", f"{item.gain:.2f} db")
            cell.set_sensitive(model[iter_][1])

        column = Gtk.TreeViewColumn(_("Gain"))
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        gain_renderer = Gtk.CellRendererText()
        column.prepend(gain_renderer, True)
        column.set_cell_data_func(gain_renderer, gain_cdf)
        view.append_column(column)

        def peak_cdf(column, cell, model, iter_, *args):
            item = model[iter_][0]
            if item.gain is None or not item.done:
                cell.set_property("text", "-")
            else:
                cell.set_property("text", f"{item.peak:.2f}")
            cell.set_sensitive(model[iter_][1])

        column = Gtk.TreeViewColumn(_("Peak"))
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        peak_renderer = Gtk.CellRendererText()
        column.prepend(peak_renderer, True)
        column.set_cell_data_func(peak_renderer, peak_cdf)
        view.append_column(column)

        self.create_pipelines()
        self._timeout = None
        self._sigs = {}
        self._done = []

        self.__fill_view(view, albums)
        num_to_process = sum(int(rga.should_process) for rga in self._todo)
        template = ngettext(
            "There is %(to-process)s album to update (of %(all)s)",
            "There are %(to-process)s albums to update (of %(all)s)",
            num_to_process,
        )
        info.set_markup(
            template
            % {
                "to-process": util.bold(format_int_locale(num_to_process)),
                "all": util.bold(format_int_locale(len(self._todo))),
            }
        )
        self.connect("destroy", self.__destroy)
        self.connect("response", self.__response)

    def create_pipelines(self):
        # create as many pipelines as threads
        self.pipes = [ReplayGainPipeline() for _ in range(get_num_threads())]

    def __fill_view(self, view, albums):
        self._todo = [RGAlbum.from_songs(a, self.process_mode) for a in albums]
        self._count = len(self._todo)
        self.model = model = Gtk.TreeStore(object, bool)
        insert = model.insert
        for album in reversed(self._todo):
            enabled = album.should_process
            base = insert(None, 0, row=[album, enabled])
            for song in reversed(album.songs):
                insert(base, 0, row=[song, enabled])
        view.set_model(model)

        if len(self._todo) == 1:
            view.expand_all()

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
            album = self.get_next_album()
            if not album:
                return
            p.start(album)

    def get_next_album(self):
        next_album = None
        while not next_album:
            if not self._todo:
                print_d("No more albums to process")
                return None
            next_album = self._todo.pop(0)
            if not next_album.should_process:
                print_d(f"{next_album.title} needs no processing")
                self._done.append(next_album)
                self.__update_view_for(next_album)
                next_album = None
        return next_album

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
        next_album = self.get_next_album()
        if next_album:
            pipeline.start(next_album)
        self.__update_view_for(album)

    def __update_view_for(self, album):
        for row in self.model:
            row_album = row[0]
            if row_album is album:
                self.model.row_changed(row.path, row.iter)
                break

    def __request_update(self):
        GLib.source_remove(self._timeout)
        self._timeout = None
        # all done, stop
        if len(self._done) < self._count:
            for p in self.pipes:
                p.request_update()
            self._timeout = GLib.timeout_add(400, self.__request_update)
        return False


class ReplayGain(SongsMenuPlugin, PluginConfigMixin):
    PLUGIN_ID = "ReplayGain"
    PLUGIN_NAME = _("Replay Gain")
    PLUGIN_DESC_MARKUP = _(
        'Analyzes and updates <a href="%(rg_link)s">ReplayGain</a> information, '
        "using GStreamer. Results are grouped by album."
    ) % {"rg_link": "https://wikipedia.org/wiki/ReplayGain"}
    PLUGIN_ICON = Icons.MULTIMEDIA_VOLUME_CONTROL
    CONFIG_SECTION = "replaygain"

    plugin_handles = each_song(is_finite, is_writable)

    def plugin_albums(self, albums):
        mode = self.config_get("process_if", UpdateMode.ALWAYS)
        win = RGDialog(albums, parent=self.plugin_window, process_mode=mode)
        win.show_all()
        win.start_analysis()

        # plugin_done checks for metadata changes and opens the write dialog
        win.connect("destroy", self.__plugin_done)

    def __plugin_done(self, win):
        self.plugin_finish()

    @classmethod
    def PluginPreferences(cls, parent):
        vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        # Tabulate all settings for neatness
        table = Gtk.Table(n_rows=1, n_columns=2)
        table.props.expand = False
        table.set_col_spacings(6)
        table.set_row_spacings(6)
        rows = []

        def process_option_changed(combo):
            model = combo.get_model()
            lbl, value = model[combo.get_active()]
            cls.config_set("process_if", value)

        def create_model():
            model = Gtk.ListStore(str, str)
            model.append([util.bold(_("always")), UpdateMode.ALWAYS])
            model.append(
                [_("if <b>any</b> RG tags are missing"), UpdateMode.ANY_MISSING]
            )
            model.append(
                [_("if <b>album</b> RG tags are missing"), UpdateMode.ALBUM_MISSING]
            )
            return model

        def set_active(value):
            for i, item in enumerate(model):
                if value == item[1]:
                    combo.set_active(i)

        model = create_model()
        combo = Gtk.ComboBox(model=model)
        set_active(cls.config_get("process_if", UpdateMode.ALWAYS))
        renderer = Gtk.CellRendererText()
        combo.connect("changed", process_option_changed)
        combo.prepend(renderer, True)
        combo.add_attribute(renderer, "markup", 0)

        rows.append((_("_Process albums:"), combo))

        for row, (label_text, entry) in enumerate(rows):
            label = Gtk.Label(label=label_text)
            label.set_alignment(0.0, 0.5)
            label.set_use_underline(True)
            label.set_mnemonic_widget(entry)
            table.attach(label, 0, 1, row, row + 1, xoptions=Gtk.AttachOptions.FILL)
            table.attach(entry, 1, 2, row, row + 1)

        # Server settings Frame
        frame = Frame(_("Existing Tags"), table)

        vb.prepend(frame, True, True, 0)
        return vb


if not Gst.Registry.get().find_plugin("replaygain"):
    __all__ = []
    del ReplayGain
    raise MissingGstreamerElementPluginError("replaygain", "good")
