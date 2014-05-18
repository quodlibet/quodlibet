# Copyright 2011,2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import multiprocessing

from gi.repository import Gtk, Pango, GLib

from quodlibet.qltk import Button, Window

from .musicdns import MusicDNSThread
from .acoustid import AcoustidSubmissionThread
from .analyze import FingerPrintThreadPool
from .util import get_puid_lookup


class FingerprintDialog(Window):
    def __init__(self, songs):
        super(FingerprintDialog, self).__init__()
        self.set_border_width(12)
        self.set_title(_("Submit Acoustic Fingerprints"))
        self.set_default_size(300, 0)

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
        expand = Gtk.Expander.new_with_mnemonic(_("_Details"))
        align = Gtk.Alignment.new(0.0, 0.0, 1.0, 1.0)
        align.set_padding(6, 0, 6, 0)
        expand.add(align)
        align.add(stats)

        def expand_cb(expand, *args):
            self.resize(self.get_size()[0], 1)
        stats.connect("unmap", expand_cb)

        box.pack_start(expand, False, False, 0)

        self.__fp_results = {}
        self.__fp_done = 0
        self.__songs = songs
        self.__musicdns_thread = None
        self.__acoustid_thread = None

        self.__invalid_songs = set()
        self.__mbids = self.__puids = self.__meta = 0
        for song in self.__songs:
            got_puid = bool(song("puid"))
            got_mbid = bool(song("musicbrainz_trackid"))
            got_meta = bool(song("artist") and song.get("title")
                and song("album"))

            if not got_puid and not got_mbid and not got_meta:
                self.__invalid_songs.add(song)

            self.__puids += got_puid
            self.__mbids += got_mbid
            self.__meta += got_meta

        self.__update_stats()

        pool = FingerPrintThreadPool(multiprocessing.cpu_count())

        bbox = Gtk.HButtonBox()
        bbox.set_layout(Gtk.ButtonBoxStyle.END)
        bbox.set_spacing(6)
        self.__submit = submit = Button(_("_Submit"), Gtk.STOCK_APPLY)
        submit.set_sensitive(False)
        submit.connect('clicked', self.__submit_cb)
        cancel = Gtk.Button(stock=Gtk.STOCK_CANCEL)
        cancel.connect_object('clicked', self.__cancel_cb, pool)
        bbox.pack_start(submit, True, True, 0)
        bbox.pack_start(cancel, True, True, 0)

        outer_box.pack_start(box, False, True, 0)
        outer_box.pack_start(bbox, False, True, 0)

        pool.connect('fingerprint-done', self.__fp_done_cb)
        pool.connect('fingerprint-error', self.__fp_error_cb)
        pool.connect('fingerprint-started', self.__fp_started_cb)

        for song in songs:
            option = get_puid_lookup()
            if option == "no_mbid":
                ofa = not song("musicbrainz_trackid") and not song("puid")
            elif option == "always":
                ofa = not song("puid")
            else:
                ofa = False
            pool.push(song, ofa=ofa)

        self.connect_object('delete-event', self.__cancel_cb, pool)

        self.add(outer_box)
        self.show_all()

    def __update_stats(self):
        all = len(self.__songs)
        to_send = all - len(self.__invalid_songs)
        valid_fp = len(self.__fp_results)

        text = _("Songs either need a <i><b>musicbrainz_trackid</b></i>, "
            "a <i><b>puid</b></i>\nor <i><b>artist</b></i> / "
            "<i><b>title</b></i> / <i><b>album</b></i> tags to get submitted.")
        text += _("\n\n<i>Fingerprints:</i> %d/%d") % (valid_fp, all)
        text += _("\n<i>Songs with MBIDs:</i> %d/%d") % (self.__mbids, all)
        text += _("\n<i>Songs with PUIDs:</i> %d/%d") % (self.__puids, all)
        text += _("\n<i>Songs with sufficient tags:</i> %d/%d") % (
            self.__meta, all)
        text += _("\n<i>Songs to submit:</i> %d/%d") % (to_send, all)
        self.__stats.set_markup(text)

    def __filter_results(self):
        """Returns a copy of all results which are suitable for sending"""
        to_send = {}
        for song, data in self.__fp_results.iteritems():
            artist = song("artist")
            title = song.get("title", "") # title falls back to filename
            album = song("album")
            puid = song("puid") or data.get("puid", "")
            mbid = song("musicbrainz_trackid")
            if mbid or puid or (artist and title and album):
                to_send[song] = data
        return to_send

    def __set_fraction(self, progress):
        self.__bar.set_fraction(progress)
        self.__bar.set_text("%d%%" % round(progress * 100))

    def __set_fp_fraction(self):
        self.__fp_done += 1
        frac = self.__fp_done / float(len(self.__songs))
        self.__set_fraction(frac)
        if self.__fp_done == len(self.__songs):
            GLib.timeout_add(500, self.__start_puid)

    def __fp_started_cb(self, pool, song):
        # increase by an amount smaller than one song, so that the user can
        # see some progress from the beginning.
        self.__set_fraction(0.5 / len(self.__songs) +
            self.__bar.get_fraction())
        self.__label_song.set_text(song("~filename"))

    def __fp_done_cb(self, pool, song, result):
        # fill in song duration if gstreamer failed
        result.setdefault("length", song("~#length") * 1000)
        self.__fp_results[song] = result
        self.__set_fp_fraction()
        self.__update_stats()

    def __fp_error_cb(self, pool, song, error):
        print_w("[fingerprint] " + error)
        self.__invalid_songs.add(song)
        self.__set_fp_fraction()
        self.__update_stats()

    def __start_puid(self):
        for song, data in self.__fp_results.iteritems():
            if "ofa" in data:
                self.__label.set_markup("<b>%s</b>" % _("Looking up PUIDs:"))
                self.__set_fraction(0)
                self.__musicdns_thread = MusicDNSThread(self.__fp_results,
                    self.__puid_update, self.__puid_done)
                break
        else:
            self.__submit.set_sensitive(True)

    def __show_final_stats(self):
        all = len(self.__songs)
        to_send = all - len(self.__invalid_songs)
        self.__label_song.set_text(
            _("Done. %d/%d songs to submit.") % (to_send, all))

    def __puid_done(self, thread):
        thread.join()
        self.__set_fraction(1.0)
        self.__show_final_stats()
        self.__submit.set_sensitive(True)

    def __puid_update(self, song, progress):
        self.__label_song.set_text(song("~filename"))
        self.__set_fraction(progress)

        if song in self.__fp_results and "puid" in self.__fp_results[song]:
            self.__puids += 1
            self.__invalid_songs.discard(song)

        self.__update_stats()

    def __cancel_cb(self, pool, *args):
        self.destroy()

        def idle_cancel():
            pool.stop()
            if self.__musicdns_thread:
                self.__musicdns_thread.stop()
            if self.__acoustid_thread:
                self.__acoustid_thread.stop()
        # pool.stop can block a short time because the CV might be locked
        # during starting the pipeline -> idle_add -> no GUI blocking
        GLib.idle_add(idle_cancel)

    def __submit_cb(self, *args):
        self.__submit.set_sensitive(False)
        self.__label.set_markup("<b>%s</b>" % _("Submitting Fingerprints:"))
        self.__set_fraction(0)
        self.__acoustid_thread = AcoustidSubmissionThread(
            self.__fp_results, self.__invalid_songs,
            self.__acoustid_update, self.__acoustid_done)

    def __acoustid_update(self, progress):
        self.__set_fraction(progress)
        self.__label_song.set_text(_("Submitting..."))

    def __acoustid_done(self, thread):
        thread.join()
        self.__set_fraction(1.0)
        self.__show_final_stats()
        GLib.timeout_add(500, self.destroy)
