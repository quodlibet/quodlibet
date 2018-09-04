# -*- coding: utf-8 -*-
# Copyright 2011,2013 Christoph Reiter
#                2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk, Pango, GLib

from quodlibet import _
from quodlibet.qltk import Button, Window
from quodlibet.util import connect_obj, print_w

from .acoustid import AcoustidSubmissionThread
from .analyze import FingerPrintPool


def get_stats(results):
    got_mbid = got_meta = 0

    for result in results:
        song = result.song
        got_mbid += bool(song("musicbrainz_trackid"))
        got_meta += bool(
            song("artist") and song.get("title") and song("album"))

    return got_mbid, got_meta


def can_submit(result):
    got_mbid, got_meta = get_stats([result])
    return bool(got_mbid or got_meta)


class FingerprintDialog(Window):
    def __init__(self, songs):
        super(FingerprintDialog, self).__init__()
        self.set_border_width(12)
        self.set_title(_("Submit Acoustic Fingerprints"))
        self.set_default_size(450, 0)

        outer_box = Gtk.VBox(spacing=12)

        box = Gtk.VBox(spacing=6)

        self.__label = label = Gtk.Label()
        label.set_markup("<b>%s</b>" % _("Generating fingerprints:"))
        label.set_alignment(0, 0.5)
        box.pack_start(label, False, True, 0)

        self.__bar = bar = Gtk.ProgressBar()
        self.__set_fraction(0)
        box.pack_start(bar, False, True, 0)
        self.__label_song = label_song = Gtk.Label()
        label_song.set_alignment(0, 0.5)
        label_song.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        box.pack_start(label_song, False, True, 0)

        self.__stats = stats = Gtk.Label()
        stats.set_alignment(0, 0.5)
        stats.set_line_wrap(True)
        stats.set_size_request(426, -1)
        expand = Gtk.Expander.new_with_mnemonic(_("_Details"))
        expand.set_resize_toplevel(True)
        expand.add(stats)

        def expand_cb(expand, *args):
            self.resize(self.get_size()[0], 1)
        stats.connect("unmap", expand_cb)

        box.pack_start(expand, False, False, 0)

        self.__fp_results = {}
        self.__fp_done = 0
        self.__songs = songs
        self.__musicdns_thread = None
        self.__acoustid_thread = None

        self.__update_stats()

        pool = FingerPrintPool()

        bbox = Gtk.HButtonBox()
        bbox.set_layout(Gtk.ButtonBoxStyle.END)
        bbox.set_spacing(6)
        self.__submit = submit = Button(_("_Submit"))
        submit.set_sensitive(False)
        submit.connect('clicked', self.__submit_cb)
        cancel = Button(_("_Cancel"))
        connect_obj(cancel, 'clicked', self.__cancel_cb, pool)
        bbox.pack_start(cancel, True, True, 0)
        bbox.pack_start(submit, True, True, 0)

        outer_box.pack_start(box, True, True, 0)
        outer_box.pack_start(bbox, False, True, 0)

        pool.connect('fingerprint-done', self.__fp_done_cb)
        pool.connect('fingerprint-error', self.__fp_error_cb)
        pool.connect('fingerprint-started', self.__fp_started_cb)

        for song in songs:
            pool.push(song)

        connect_obj(self, 'delete-event', self.__cancel_cb, pool)

        self.add(outer_box)
        self.show_all()

    def __update_stats(self):
        all_ = len(self.__songs)
        results = self.__fp_results.values()
        to_send = len(list(filter(can_submit, results)))
        valid_fp = len(results)
        got_mbid, got_meta = get_stats(results)

        text = _("Songs either need a <i><b>musicbrainz_trackid</b></i>, "
            "or <i><b>artist</b></i> / "
            "<i><b>title</b></i> / <i><b>album</b></i> tags to get submitted.")
        text += "\n\n" + "<i>%s</i>" % _("Fingerprints:")
        text += " %d/%d" % (valid_fp, all_)
        text += "\n" + "<i>%s</i>" % _("Songs with MBIDs:")
        text += " %d/%d" % (got_mbid, all_)
        text += "\n" + "<i>%s</i>" % _("Songs with sufficient tags:")
        text += " %d/%d" % (got_meta, all_)
        text += "\n" + "<i>%s</i>" % _("Songs to submit:")
        text += " %d/%d" % (to_send, all_)
        self.__stats.set_markup(text)

    def __set_fraction(self, progress):
        self.__bar.set_fraction(progress)
        self.__bar.set_text("%d%%" % round(progress * 100))

    def __inc_fp_fraction(self):
        self.__fp_done += 1
        frac = self.__fp_done / float(len(self.__songs))
        self.__set_fraction(frac)
        if self.__fp_done == len(self.__songs):
            self.__submit.set_sensitive(True)
            self.__show_final_stats()

    def __fp_started_cb(self, pool, song):
        # increase by an amount smaller than one song, so that the user can
        # see some progress from the beginning.
        self.__set_fraction(0.5 / len(self.__songs) +
            self.__bar.get_fraction())
        self.__label_song.set_text(song("~filename"))

    def __fp_done_cb(self, pool, result):
        self.__fp_results[result.song] = result
        self.__inc_fp_fraction()
        self.__update_stats()

    def __fp_error_cb(self, pool, song, error):
        print_w("[fingerprint] " + error)
        self.__inc_fp_fraction()
        self.__update_stats()

    def __show_final_stats(self):
        all_ = len(self.__songs)
        results = self.__fp_results.values()
        to_send = len(list(filter(can_submit, results)))
        self.__label_song.set_text(
            _("Done. %(to-send)d/%(all)d songs to submit.") % {
                "to-send": to_send, "all": all_})

    def __cancel_cb(self, pool, *args):
        self.destroy()

        def idle_cancel():
            pool.stop()
            if self.__acoustid_thread:
                self.__acoustid_thread.stop()
        # pool.stop can block a short time because the CV might be locked
        # during starting the pipeline -> idle_add -> no GUI blocking
        GLib.idle_add(idle_cancel)

    def __submit_cb(self, *args):
        self.__submit.set_sensitive(False)
        self.__label.set_markup("<b>%s</b>" % _("Submitting fingerprints:"))
        self.__set_fraction(0)
        self.__acoustid_thread = AcoustidSubmissionThread(
            list(filter(can_submit, self.__fp_results.values())),
            self.__acoustid_update, self.__acoustid_done)

    def __acoustid_update(self, progress):
        self.__set_fraction(progress)
        self.__label_song.set_text(_(u"Submitting…"))

    def __acoustid_done(self):
        self.__acoustid_thread.join()
        self.__set_fraction(1.0)
        GLib.timeout_add(500, self.destroy)
