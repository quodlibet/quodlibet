#! /usr/bin/env python
#
#    ReplayGain Album Analysis using gstreamer rganalysis element
#    Copyright (C) 2005,2007,2009  Michael Urman
#                            2012  Nick Boultbee
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of version 2 of the GNU General Public License as
#    published by the Free Software Foundation.
#

from gi.repository import Gtk, GLib, Pango, Gst

from quodlibet.plugins.songsmenu import SongsMenuPlugin

__all__ = ['ReplayGain']

class ReplayGain(SongsMenuPlugin):
    PLUGIN_ID = 'ReplayGain'
    PLUGIN_NAME = 'Replay Gain'
    PLUGIN_DESC = _('Analyzes ReplayGain with gstreamer, grouped by album')
    PLUGIN_ICON = Gtk.STOCK_MEDIA_PLAY
    PLUGIN_VERSION = "2.3"

    def plugin_albums(self, albums):
        win = Gtk.Dialog(title='ReplayGain', parent=self.plugin_window,
                buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                    Gtk.STOCK_SAVE, Gtk.ResponseType.OK))
        win.set_default_size(500, 350)
        win.set_border_width(6)
        swin = Gtk.ScrolledWindow()
        win.vbox.pack_start(swin, True, True, 0)
        swin.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        swin.set_shadow_type(Gtk.ShadowType.IN)
        from quodlibet.qltk.views import HintedTreeView
        model = Gtk.TreeStore(object, str, int, str, str)
        view = HintedTreeView(model)
        swin.add(view)
        err_lbl = Gtk.Label(label="%s\n%s" % (
                _("One or more songs could not be analyzed.)"),
                _("Data for these songs will not be written.")))
        err_lbl.set_child_visible(False)
        win.vbox.pack_start(err_lbl, False, True, 0)

        # Create a view of title/progress/gain/peak for each track + album
        col = Gtk.TreeViewColumn('Track',
            Gtk.CellRendererText(ellipsize=Pango.EllipsizeMode.END),
            text=1)
        col.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        col.set_expand(True)
        col.set_fixed_width(120)
        view.append_column(col)

        col = Gtk.TreeViewColumn(_('Progress'),
                Gtk.CellRendererProgress(), value=2)
        col.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        view.append_column(col)

        col = Gtk.TreeViewColumn(_('Gain'), Gtk.CellRendererText(), text=3)
        col.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        view.append_column(col)

        col = Gtk.TreeViewColumn(_('Peak'), Gtk.CellRendererText(), text=4)
        col.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        view.append_column(col)

        for album in albums:
            album_heading = album[0]('~artist~album').replace("\n", ", ")
            base = model.append(None,
                [None, album_heading, 0, "-", "-"])
            for s in album:
                model.append(base,
                    [s, s('~tracknumber~title~version'), 0, "-", "-"])

        win.connect("destroy", self.__plugin_done)
        win.vbox.show_all()
        win.present()

        # kick off the analysis
        analysis = Analysis(win, view, model)
        analysis.next_song()

    def __plugin_done(self, win):
        self.plugin_finish()


class Analysis(object):
    error_str = "Error!"

    def __init__(self, win, view, model):
        # bookkeeping
        self.win = win
        self.win.connect('response', self.response)
        GLib.timeout_add(450, self.progress)
        self.set_finished(False)
        self.view = view
        self.model = model
        self.album = model.get_iter_first()
        self.song = None
        self.current = None

        # gst pipeline for replay gain analysis:
        # filesrc!decodebin!audioconvert!audioresample!rganalysis!fakesink
        self.pipe = Gst.Pipeline()
        self.filesrc = Gst.ElementFactory.make("filesrc", "source")
        self.pipe.add(self.filesrc)

        self.decode = Gst.ElementFactory.make("decodebin", "decode")
        self.decode.connect("pad-added", self.new_decoded_pad)
        self.decode.connect("pad-removed", self.removed_decoded_pad)
        self.pipe.add(self.decode)
        self.filesrc.link(self.decode)

        self.convert = Gst.ElementFactory.make("audioconvert", "convert")
        self.pipe.add(self.convert)

        self.resample = Gst.ElementFactory.make("audioresample", "resample")
        self.pipe.add(self.resample)
        self.convert.link(self.resample)

        self.analysis = Gst.ElementFactory.make("rganalysis", "analysis")
        self.nalbum = self.model.iter_n_children(self.album)
        self.analysis.set_property("num-tracks", self.nalbum)
        self.pipe.add(self.analysis)
        self.resample.link(self.analysis)

        self.sink = Gst.ElementFactory.make("fakesink", "sink")
        self.pipe.add(self.sink)
        self.analysis.link(self.sink)

        bus = self.pipe.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.bus_message)

    def new_decoded_pad(self, dbin, pad):
        pad.link(self.convert.get_static_pad("sink"))

    def removed_decoded_pad(self, dbin, pad):
        pad.unlink(self.convert.get_static_pad("sink"))

    def bus_message(self, bus, message):
        if message.type == Gst.MessageType.TAG:
            # FIXME: Find a way to get the creator of the tags.
            # all tags have the sink as source now and since decodebin
            # also posts tags on the bus we can't be sure if the
            # tags are new or old ones

            track = self.model[self.song]
            album = self.model[self.album]

            tags = message.parse_tag()
            ok, value = tags.get_double(Gst.TAG_TRACK_GAIN)
            if ok:
                track[3] = '%.2f dB' % value

            ok, value = tags.get_double(Gst.TAG_TRACK_PEAK)
            if ok:
                track[4] = '%.4f' % value

            # FIXME: GIPORT
            return

            if album[3] == self.error_str:
                return

            ok, value = tags.get_double(Gst.TAG_ALBUM_GAIN)
            if ok:
                album[3] = '%.2f dB' % value

            ok, value = tags.get_double(Gst.TAG_ALBUM_PEAK)
            if ok:
                album[4] = '%.4f' % value
        elif message.type == Gst.MessageType.EOS:
            self.next_song()
        elif message.type == Gst.MessageType.ERROR:
            err_lbl = self.win.vbox.get_children()[1]
            err_lbl.set_child_visible(True)
            err_lbl.show()
            track = self.model[self.song]
            track[3] = self.error_str
            track[4] = self.error_str
            album = self.model[self.album]
            album[3] = self.error_str
            album[4] = self.error_str
            self.next_song()

    def next_song(self):
        if self.song is None:
            self.view.expand_row(self.model.get_path(self.album), False)
            self.song = self.model.iter_children(self.album)
            self.nsong = 0
        else:
            self.song = self.model.iter_next(self.song)
            self.nsong += 1
            # preserve rganalysis state across files
            # FIXME: GIPORT
            #self.analysis.set_locked_state(True)
            self.pipe.set_state(Gst.State.NULL)

        if self.current:
            # make sure progress hits full
            self.current[2] = 100
            self.model[self.album][2] = int(100 * self.nsong / self.nalbum)

        if self.song is None:
            self.pipe.set_state(Gst.State.NULL)
            self.view.collapse_row(self.model.get_path(self.album))
            self.album = self.model.iter_next(self.album)
            if self.album is None:
                self.set_finished(True)
            else:
                self.nalbum = self.model.iter_n_children(self.album)
                self.analysis.set_property("num-tracks", self.nalbum)
                self.next_song()
        else:
            self.view.scroll_to_cell(self.model.get_path(self.song))
            self.current = self.model[self.song]
            self.filesrc.set_property("location", self.current[0]['~filename'])
            self.pipe.set_state(Gst.State.PLAYING)
            self.analysis.set_locked_state(False)

    def progress(self):
        song = self.current and self.current[0]
        if not song:
            return False

        ok, p = self.pipe.query_position(Gst.Format.TIME)
        if ok:
            p //= Gst.MSECOND * 10
            self.current[2] = sp = \
                int(p / (song.get("~#length", 0) or 2 * p or 1))
            ap = int((sp + 100 * self.nsong) / self.nalbum)
            self.model[self.album][2] = ap

        return True

    def set_finished(self, done):
        # enable/disable the save button
        try:
            buttons = self.win.vbox.get_children()[2].get_children()
        except IndexError:
            pass
        else:
            buttons[0].set_sensitive(done)

        if done:
            self.current = None
            self.analysis.set_locked_state(False)

    def response(self, win, response):
        # kill the pipeline in case this is a cancel
        self.pipe.set_state(Gst.State.NULL)
        self.set_finished(True)

        # save only if response says to
        if response != Gtk.ResponseType.OK:
            win.destroy()
            return

        ialbum = self.model.get_iter_first()
        while ialbum is not None:
            album = self.model[ialbum]
            albumgain = album[3]
            albumpeak = album[4]

            itrack = self.model.iter_children(ialbum)
            ialbum = self.model.iter_next(ialbum)
            while itrack is not None:
                track = self.model[itrack]
                itrack = self.model.iter_next(itrack)
                song = track[0]
                if song is None:
                    continue

                trackgain = track[3]
                trackpeak = track[4]

                if trackgain == self.error_str:
                    continue

                if trackgain != '-':
                    song['replaygain_track_gain'] = trackgain
                if trackpeak != '-':
                    song['replaygain_track_peak'] = trackpeak
                if albumgain != '-' and albumgain != self.error_str:
                    song['replaygain_album_gain'] = albumgain
                if albumpeak != '-' and albumgain != self.error_str:
                    song['replaygain_album_peak'] = albumpeak

        win.destroy()

if not Gst.Registry.get().find_plugin("replaygain"):
    __all__ = []
    del ReplayGain
    raise ImportError("GStreamer replaygain plugin not found")
