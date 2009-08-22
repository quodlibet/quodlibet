#! /usr/bin/env python
#
#    ReplayGain Album Analysis using gstreamer rganalysis element
#    Copyright (C) 2005,2007,2009  Michael Urman
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of version 2 of the GNU General Public License as
#    published by the Free Software Foundation.
#

import gtk
import gobject
import pango
import gst

__all__ = ['ReplayGain']
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet import stock

class ReplayGain(SongsMenuPlugin):
    PLUGIN_ID = 'ReplayGain'
    PLUGIN_NAME = 'Replay Gain'
    PLUGIN_DESC = 'Analyzes ReplayGain with gstreamer, grouped by album'
    PLUGIN_ICON = stock.VOLUME_MED
    PLUGIN_VERSION = "2.2"

    def plugin_albums(self, albums):
        win = gtk.Dialog(title='ReplayGain',
                buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                    gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        win.set_default_size(400, 300)
        win.set_border_width(6)
        swin = gtk.ScrolledWindow()
        win.vbox.pack_start(swin)
        swin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        swin.set_shadow_type(gtk.SHADOW_IN)
        from quodlibet.qltk.views import HintedTreeView
        model = gtk.TreeStore(object, str, int, str, str)
        view = HintedTreeView(model)
        swin.add(view)
        err_lbl = gtk.Label("One or more songs could not be analyzed.\n"
                "Data for these songs will not be written.")
        err_lbl.set_child_visible(False)
        win.vbox.pack_start(err_lbl, expand=False)

        # Create a view of title/progress/gain/peak for each track + album
        col = gtk.TreeViewColumn('Track',
            gobject.new(gtk.CellRendererText, ellipsize=pango.ELLIPSIZE_END),
            text=1)
        col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        col.set_expand(True)
        col.set_fixed_width(120)
        view.append_column(col)

        col = gtk.TreeViewColumn('Progress',
                gtk.CellRendererProgress(), value=2)
        col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        view.append_column(col)

        col = gtk.TreeViewColumn('Gain', gtk.CellRendererText(), text=3)
        col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        view.append_column(col)

        col = gtk.TreeViewColumn('Peak', gtk.CellRendererText(), text=4)
        col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        view.append_column(col)

        for album in albums:
            base = model.append(None,
                [None, album[0]('~artist~album'), 0, "-", "-"])
            for s in album:
                model.append(base,
                    [s, s('~tracknumber~title~version'), 0, "-", "-"])

        win.vbox.show_all()
        win.present()
        win.finished = False

        # kick off the analysis
        analysis = Analysis(win, view, model)
        analysis.next_song()

        # wait for the dialog to be closed
        while not win.finished:
            gtk.main_iteration()

        win.hide()
        win.destroy()

class Analysis(object):
    error_str = "Error!"

    def __init__(self, win, view, model):
        # bookkeeping
        self.win = win
        self.win.connect('response', self.response)
        gobject.timeout_add(450, self.progress)
        self.set_finished(False)
        self.view = view
        self.model = model
        self.album = model.get_iter_first()
        self.song = None
        self.current = None

        # gst pipeline for replay gain analysis:
        # filesrc!decodebin!audioconvert!audioresample!rganalysis!fakesink
        self.pipe = gst.Pipeline("pipe")
        self.filesrc = gst.element_factory_make("filesrc", "source")
        self.pipe.add(self.filesrc)

        self.decode = gst.element_factory_make("decodebin", "decode")
        self.decode.connect("new-decoded-pad", self.new_decoded_pad)
        self.decode.connect("removed-decoded-pad", self.removed_decoded_pad)
        self.pipe.add(self.decode)
        self.filesrc.link(self.decode)

        self.convert = gst.element_factory_make("audioconvert", "convert")
        self.pipe.add(self.convert)

        self.resample = gst.element_factory_make("audioresample", "resample")
        self.pipe.add(self.resample)
        self.convert.link(self.resample)

        self.analysis = gst.element_factory_make("rganalysis", "analysis")
        self.nalbum = self.model.iter_n_children(self.album)
        self.analysis.set_property("num-tracks", self.nalbum)
        self.pipe.add(self.analysis)
        self.resample.link(self.analysis)

        self.sink = gst.element_factory_make("fakesink", "sink")
        self.pipe.add(self.sink)
        self.analysis.link(self.sink)

        bus = self.pipe.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.bus_message)

    def new_decoded_pad(self, dbin, pad, islast):
        pad.link(self.convert.get_pad("sink"))

    def removed_decoded_pad(self, dbin, pad):
        pad.unlink(self.convert.get_pad("sink"))

    def bus_message(self, bus, message):
        if message.type == gst.MESSAGE_TAG:
            if message.src == self.analysis:
                tags = message.parse_tag()
                track = self.model[self.song]
                album = self.model[self.album]
                try:
                    track[3] = '%.2f dB' % tags[gst.TAG_TRACK_GAIN]
                    track[4] = '%.4f' % tags[gst.TAG_TRACK_PEAK]
                except KeyError: pass
                try:
                    if album[3] != self.error_str:
                        album[3] = '%.2f dB' % tags[gst.TAG_ALBUM_GAIN]
                        album[4] = '%.4f' % tags[gst.TAG_ALBUM_PEAK]
                except KeyError: pass
        elif message.type == gst.MESSAGE_EOS:
            self.next_song()
        elif message.type == gst.MESSAGE_ERROR:
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
            self.analysis.set_locked_state(True)
            self.pipe.set_state(gst.STATE_NULL)

        if self.current:
            # make sure progress hits full
            self.current[2] = 100
            self.model[self.album][2] = int(100 * self.nsong / self.nalbum)

        if self.song is None:
            self.pipe.set_state(gst.STATE_NULL)
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
            self.pipe.set_state(gst.STATE_PLAYING)
            self.analysis.set_locked_state(False)

    def progress(self):
        song = self.current and self.current[0]
        if not song:
            return False

        try:
            p = self.pipe.query_position(gst.FORMAT_TIME)[0]
        except gst.QueryError:
            pass
        else:
            p //= gst.MSECOND * 10
            self.current[2] = sp = int(p / (song("~#length") or 2 * p or 1))
            ap = int((sp + 100 * self.nsong) / self.nalbum)
            self.model[self.album][2] = ap

        return True

    def set_finished(self, done):
        # enable/disable the save button
        try:
            buttons = self.win.vbox.get_children()[3].get_children()
        except IndexError:
            pass
        else:
            buttons[0].set_sensitive(done)

        if done:
            self.current = None
            self.analysis.set_locked_state(False)

    def response(self, win, response):
        # kill the pipeline in case this is a cancel
        self.pipe.set_state(gst.STATE_NULL)
        self.set_finished(True)
        self.win.finished = True

        # save only if response says to
        if response != gtk.RESPONSE_OK:
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

if gst.registry_get_default() is gst:
    import sys
    del sys.modules['gst']
    import pygst
    pygst.require('0.10')
    import gst

if not gst.registry_get_default().find_plugin("replaygain"):
    __all__ = []
    del ReplayGain
    raise gst.PluginNotFoundError("replaygain")
