# Copyright 2011 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gst
import gobject
import gtk
import pango

import threading
import random
import urllib
import urllib2
import StringIO
import gzip
from xml.dom.minidom import parseString

from quodlibet import config
from quodlibet import util
from quodlibet.qltk import Button, Window, Frame
from quodlibet.qltk.entry import UndoEntry
from quodlibet.qltk.msg import ErrorMessage
from quodlibet.plugins.songsmenu import SongsMenuPlugin

def get_num_threads():
    # multiprocessing is >= 2.6.
    # Default to 2 threads if cpu_count isn't implemented for the current arch
    # or multiprocessing isn't available
    try:
        import multiprocessing
        threads = multiprocessing.cpu_count()
    except (ImportError, NotImplementedError): threads = 2
    return threads

class FingerPrintPipeline(threading.Thread):
    def __init__(self, pool, song, ofa):
        super(FingerPrintPipeline, self).__init__()
        self.daemon = True

        self.__pool = pool
        self.__song = song
        self.__cv = threading.Condition()
        self.__shutdown = False
        self.__ofa = ofa
        self.__fingerprints = {}
        self.__todo = []

        self.start()

    def run(self):
        # TODO: change playbin to uridecodebin / filesrc+decodebin?

        # I sometimes get:
        # GStreamer-CRITICAL **:
        # Trying to dispose element test, but it is in READY
        # instead of the NULL state.
        #
        # GStreamer problem? Getting rid of playbin might fix this too..

        gbin = gst.Bin()

        tee = gst.element_factory_make("tee")
        gbin.add(tee)

        chroma = ["queue", "chromaprint", "fakesink"]
        chroma = map(gst.element_factory_make, chroma)
        map(gbin.add, chroma)
        gst.element_link_many(tee, *chroma)
        self.__todo = [chroma[1]]

        if self.__ofa and gst.element_factory_find("ofa"):
            ofa = ["queue", "ofa", "fakesink"]
            ofa = map(gst.element_factory_make, ofa)
            map(gbin.add, ofa)
            gst.element_link_many(tee, *ofa)
            self.__todo += [ofa[1]]

        gbin.add_pad(gst.GhostPad('sink', tee.get_pad('sink')))

        # playbin
        playbin = gst.element_factory_make("playbin")
        playbin.set_property('audio-sink', gbin)
        video_fake = gst.element_factory_make('fakesink')
        playbin.set_property('video-sink', video_fake)
        playbin.set_property('uri', self.__song("~uri"))

        # bus
        bus = playbin.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("sync-message", self.__bus_message, chroma[1],
            self.__ofa and ofa[1])

        # get it started
        self.__cv.acquire()
        playbin.set_state(gst.STATE_PLAYING)

        result = playbin.get_state()[0]
        if result == gst.STATE_CHANGE_FAILURE:
            # something failed, error message kicks in before, so check
            # for shutdown
            if not self.__shutdown:
                self.__shutdown = True
                gobject.idle_add(self.__pool._callback, self.__song,
                    None, "Error", self)
        elif not self.__shutdown:
            # GStreamer probably knows song durations better than we do.
            # (and it's more precise for PUID lookup)
            # In case this fails, we insert the mutagen value later
            # (this only works in active playing state)
            try: d = playbin.query_duration(gst.FORMAT_TIME)[0]
            except gst.QueryError: pass
            else: self.__fingerprints["length"] = d / gst.MSECOND

            self.__cv.wait()
        self.__cv.release()

        # clean up
        bus.remove_signal_watch()
        playbin.set_state(gst.STATE_NULL)

        # we need to make sure the state change has finished, before
        # we can return and hand it over to the python GC
        playbin.get_state()

    def stop(self):
        self.__shutdown = True
        self.__cv.acquire()
        self.__cv.notify()
        self.__cv.release()

    def __bus_message(self, bus, message, chroma, ofa):
        error = None
        if message.type == gst.MESSAGE_TAG:
            if message.src == chroma:
                self.__todo.remove(chroma)
                tags = message.parse_tag()
                key = "chromaprint-fingerprint"
                if key in tags.keys():
                    self.__fingerprints["chromaprint"] = tags[key]
            elif message.src == ofa:
                self.__todo.remove(ofa)
                tags = message.parse_tag()
                key = "ofa-fingerprint"
                if key in tags.keys():
                    self.__fingerprints["ofa"] = tags[key]
        elif message.type == gst.MESSAGE_EOS:
            # It seems that even if the song is shorter than the
            # the fingerprint duration, the tag message kicks in before eos
            # I don't know if this is timing related or on purpose.
            error = "EOS"
        elif message.type == gst.MESSAGE_ERROR:
            error = message.parse_error()[0]

        if not self.__shutdown and (not self.__todo or error):
            gobject.idle_add(self.__pool._callback, self.__song,
                self.__fingerprints, error, self)
            self.__shutdown = True
            self.__cv.acquire()
            self.__cv.notify()
            self.__cv.release()

class FingerPrintThreadPool(gobject.GObject):
    __gsignals__ = {
        "fingerprint-done": (
            gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object, object)),
        "fingerprint-started": (
            gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object,)),
        "fingerprint-error": (
            gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object, object)),
        }

    def __init__(self, max_workers):
        super(FingerPrintThreadPool, self).__init__()
        self.__threads = []
        self.__queued = []
        self.__max_workers = max_workers
        self.__stopped = False

    def push(self, song, ofa=False):
        self.__stopped = False
        if len(self.__threads) < self.__max_workers:
            self.__threads.append(FingerPrintPipeline(self, song, ofa))
            self.emit("fingerprint-started", song)
        else:
            self.__queued.append((song, ofa))

    def stop(self):
        self.__stopped = True
        for thread in self.__threads:
            thread.stop()
        for thread in self.__threads:
            thread.join()

    def _callback(self, song, result, error, thread):
        # make sure everythin is gone before starting new ones.
        thread.join()
        self.__threads.remove(thread)
        if self.__stopped: return
        if result:
            self.emit("fingerprint-done", song, result)
        else:
            self.emit("fingerprint-error", song, error)
        if self.__queued:
            song, ofa = self.__queued.pop(0)
            self.__threads.append(FingerPrintPipeline(self, song, ofa))
            self.emit("fingerprint-started", song)

class MusicDNSThread(threading.Thread):
    INTERVAL = 1500
    URL = "http://ofa.musicdns.org/ofa/1/track"
    # The anonymous keys give me quota errors. So use the picard one.
    # I hope that's ok..
    #API_KEY = "57aae6071e74345f69143baa210bda87" # anonymous
    #API_KEY = "e4230822bede81ef71cde723db743e27" # anonymous
    API_KEY = "0736ac2cd889ef77f26f6b5e3fb8a09c" # mb picard

    def __init__(self, fingerprints, progress_cb, callback):
        super(MusicDNSThread, self).__init__()
        self.__callback = callback
        self.__fingerprints = fingerprints
        self.__stopped = False
        self.__progress_cb = progress_cb
        self.__sem = threading.Semaphore()

        self.start()

    def __get_puid(self, fingerprint, duration):
        """Returns a PUID for the given libofa fingerprint and duration in
        milliseconds or None if something fails"""

        values = {
            "cid": self.API_KEY,
            "cvr": "Quod Libet",
            "fpt": fingerprint,
            "dur": str(duration), # msecs
            "brt": "",
            "fmt": "",
            "art": "",
            "ttl": "",
            "alb": "",
            "tnm": "",
            "gnr": "",
            "yrr": "",
        }

        # querying takes about 0.9 secs here, FYI
        data = urllib.urlencode(values)
        req = urllib2.Request(self.URL, data)
        error = None
        try:
            response = urllib2.urlopen(req)
        except urllib2.HTTPError, e:
            error = "urllib error, code: " + str(e.code)
        except:
            error = "urllib error"
        else:
            xml = response.read()
            try: dom = parseString(xml)
            except: error = "xml error"
            else:
                puids = dom.getElementsByTagName("puid")
                if puids and puids[0].hasAttribute("id"):
                    return puids[0].getAttribute("id")

        if error:
            print_w("[fingerprint] " + _("MusicDNS lookup failed: ") + error)

    def run(self):
        gobject.timeout_add(self.INTERVAL, self.__inc_sem)
        i = 0
        for song, data in self.__fingerprints.iteritems():
            if not "ofa" in data: continue

            puid = self.__get_puid(data["ofa"], data["length"])
            if puid: data["puid"] = puid
            i += 1

            gobject.idle_add(self.__progress_cb, song,
                float(i)/len(self.__fingerprints))

            self.__sem.acquire()
            if self.__stopped: return

        gobject.idle_add(self.__callback, self)

        # stop sem increment
        self.__stopped = True

    def __inc_sem(self):
        self.__sem.release()
        # repeat increment until stopped
        return not self.__stopped

    def stop(self):
        self.__stopped = True
        self.__sem.release()

class AcoustidSubmissionThread(threading.Thread):
    INTERVAL = 1500
    URL = "http://api.acoustid.org/v2/submit"
    APP_KEY = "C6IduH7D"
    SONGS_PER_SUBMISSION = 50 # be gentle :)

    def __init__(self, fingerprints, progress_cb, callback):
        super(AcoustidSubmissionThread, self).__init__()
        self.__callback = callback
        self.__fingerprints = fingerprints
        self.__stopped = False
        self.__progress_cb = progress_cb
        self.__sem = threading.Semaphore()
        self.__done = 0
        self.start()

    def __send(self, urldata):
        self.__done += len(urldata)

        basedata = urllib.urlencode({
            "format": "xml",
            "client": self.APP_KEY,
            "user": get_api_key(),
        })

        urldata = "&".join([basedata] + map(urllib.urlencode, urldata))
        obj = StringIO.StringIO()
        gzip.GzipFile(fileobj=obj, mode="wb").write(urldata)
        urldata = obj.getvalue()

        headers = {
            "Content-Encoding": "gzip",
            "Content-type": "application/x-www-form-urlencoded"
        }
        req = urllib2.Request(self.URL, urldata, headers)

        error = None
        try:
            response = urllib2.urlopen(req)
        except urllib2.HTTPError, e:
            error = "urllib error, code: " + str(e.code)
        except:
            error = "urllib error"
        else:
            xml = response.read()
            try: dom = parseString(xml)
            except: error = "xml error"
            else:
                status = dom.getElementsByTagName("status")
                if not status or not status[0].childNodes or not \
                    status[0].childNodes[0].nodeValue == "ok":
                    error = "response status error"

        if error:
            print_w("[fingerprint] " + _("Submission failed: ") + error)

        # emit progress
        gobject.idle_add(self.__progress_cb,
                float(self.__done)/len(self.__fingerprints))

        self.__sem.acquire()

    def run(self):
        gobject.timeout_add(self.INTERVAL, self.__inc_sem)

        urldata = []
        for i, (song, data) in enumerate(self.__fingerprints.iteritems()):
            track = {
                "duration": int(round(data["length"] / 1000)),
                "fingerprint": data["chromaprint"],
                "bitrate": song("~#bitrate"),
                "fileformat": song("~format"),
                "mbid": song("musicbrainz_trackid"),
                "puid": data.get("puid", "") or song("puid"),
                "artist": song.list("artist"),
                "album": song("album"),
                "albumartist": song("albumartist"),
                "year": song("~year"),
                "trackno": song("~#track"),
                "discno": song("~#disc"),
            }

            tuples = []
            for key, value in track.iteritems():
                # this also dismisses 0.. which should be ok here.
                if not value: continue
                # the postfixes don't have to start at a specific point,
                # they just need to be different and numbers
                key += ".%d" % i
                if isinstance(value, list):
                    for val in value:
                        tuples.append((key, val))
                else:
                    tuples.append((key, value))

            urldata.append(tuples)

            if len(urldata) >= self.SONGS_PER_SUBMISSION:
                self.__send(urldata)
                urldata = []

            if self.__stopped: return

        if urldata:
            self.__send(urldata)

        gobject.idle_add(self.__callback, self)

        # stop sem increment
        self.__stopped = True

    def __inc_sem(self):
        self.__sem.release()
        # repeat increment until stopped
        return not self.__stopped

    def stop(self):
        self.__stopped = True
        self.__sem.release()

class FingerprintDialog(Window):
    def __init__(self, songs):
        super(FingerprintDialog, self).__init__()
        self.set_border_width(12)
        self.set_title(_("Submit Acoustic Fingerprints"))
        self.set_default_size(300, 0)

        box = gtk.VBox(spacing=6)

        self.__label = label = gtk.Label()
        label.set_markup("<b>%s</b>" % _("Generating fingerprints:"))
        label.set_alignment(0, 0.5)
        box.pack_start(label, expand=False)

        self.__bar = bar = gtk.ProgressBar()
        self.__set_fraction(0)
        box.pack_start(bar, expand=False)
        self.__label_song = label_song = gtk.Label()
        label_song.set_alignment(0, 0.5)
        label_song.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
        box.pack_start(label_song, expand=False)

        self.__stats = stats = gtk.Label()
        stats.set_alignment(0, 0.5)
        expand = gtk.expander_new_with_mnemonic(_("_Details"))
        align = gtk.Alignment(xalign=0.0, yalign=0.0, xscale=1.0, yscale=1.0)
        align.set_padding(6, 0, 6, 0)
        expand.add(align)
        align.add(stats)
        def expand_cb(expand, *args):
            self.resize(self.get_size()[0], 1)
        stats.connect("unmap", expand_cb)

        box.pack_start(expand, expand=False, fill=False)

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

        pool = FingerPrintThreadPool(get_num_threads())

        bbox = gtk.HButtonBox()
        bbox.set_layout(gtk.BUTTONBOX_END)
        bbox.set_spacing(6)
        self.__submit = submit = Button(_("_Submit"), gtk.STOCK_APPLY)
        submit.set_sensitive(False)
        submit.connect('clicked', self.__submit_cb)
        cancel = gtk.Button(stock=gtk.STOCK_CANCEL)
        cancel.connect_object('clicked', self.__cancel_cb, pool)
        bbox.pack_start(submit)
        bbox.pack_start(cancel)

        box.pack_start(bbox, expand=False, fill=False)

        pool.connect('fingerprint-done', self.__fp_done_cb)
        pool.connect('fingerprint-error', self.__fp_error_cb)
        pool.connect('fingerprint-started', self.__fp_started_cb)

        # different formats have different decoding speeds, so randomizing
        # gives us a more uniform update distribution with multiple
        # threads.
        random.shuffle(songs)

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

        self.add(box)
        self.show_all()

    def __update_stats(self):
        all = len(self.__songs)
        to_send = all - len(self.__invalid_songs)

        text = _("Songs either need a <i><b>musicbrainz_trackid</b></i>, " \
            "a <i><b>puid</b></i>\nor <i><b>artist</b></i> / " \
            "<i><b>title</b></i> / <i><b>album</b></i> tags to get submitted.")
        text += _("\n\n<i>Songs with MBIDs:</i> %d/%d") % (self.__mbids, all)
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
            album  = song("album")
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
            self.__start_puid()

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

    def __fp_error_cb(self, pool, song, error):
        print_w("[fingerprint] " + error)
        self.__set_fp_fraction()

    def __start_puid(self):
        self.__musicdns_thread = MusicDNSThread(self.__fp_results,
            self.__puid_update, self.__puid_done)

    def __puid_done(self, thread):
        thread.join()
        self.__set_fraction(1.0)
        self.__label_song.set_text(_("Done"))
        self.__submit.set_sensitive(True)

    def __puid_update(self, song, progress):
        self.__label.set_markup("<b>%s</b>" % _("Looking up PUIDs:"))
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
        gobject.idle_add(idle_cancel)

    def __submit_cb(self, *args):
        self.__submit.set_sensitive(False)
        self.__acoustid_thread = AcoustidSubmissionThread(
            self.__fp_results, self.__acoustid_update, self.__acoustid_done)

    def __acoustid_update(self, progress):
        self.__label.set_markup("<b>%s</b>" % _("Submitting Fingerprints:"))
        self.__set_fraction(progress)

    def __acoustid_done(self, thread):
        thread.join()
        gobject.timeout_add(500, self.destroy)

def get_api_key():
    try:
        return config.get("plugins", "fingerprint_acoustid_api_key")
    except config.error:
        return ""

def get_puid_lookup():
    try:
        return config.get("plugins", "fingerprint_puid_lookup")
    except config.error:
        return "no_mbid"

class AcoustidSubmit(SongsMenuPlugin):
    PLUGIN_ID = "AcoustidSubmit"
    PLUGIN_NAME = _("Submit Acoustic Fingerprints")
    PLUGIN_DESC = _("Generates acoustic fingerprints using chromaprint and "
        "libofa and submits them to 'acoustid.org'")
    PLUGIN_ICON = gtk.STOCK_CONNECT
    PLUGIN_VERSION = "0.1"

    def plugin_songs(self, songs):
        if not get_api_key():
            ErrorMessage(self, _("API Key Missing"),
                _("You have to specify an Acoustid.org API key in the plugin "
                "preferences before you can submit fingerprints.")).run()
        else:
            FingerprintDialog(songs)

    @classmethod
    def PluginPreferences(self, win):
        box = gtk.VBox(spacing=12)

        # api key section
        def key_changed(entry, *args):
            config.set("plugins", "fingerprint_acoustid_api_key",
                entry.get_text())

        button = Button(_("Request API key"), gtk.STOCK_NETWORK)
        button.connect("clicked",
            lambda s: util.website("https://acoustid.org/api-key"))
        key_box = gtk.HBox(spacing=6)
        entry = UndoEntry()
        entry.set_text(get_api_key())
        entry.connect("changed", key_changed)
        label = gtk.Label(_("API _key:"))
        label.set_use_underline(True)
        label.set_mnemonic_widget(entry)
        key_box.pack_start(label, expand=False)
        key_box.pack_start(entry)
        key_box.pack_start(button, expand=False)

        box.pack_start(Frame(_("Acoustid Web Service"), child=key_box))

        # puid lookup section
        puid_box = gtk.VBox(spacing=6)
        options = [
            ("no_mbid", _("If <i>_musicbrainz__trackid</i> is missing")),
            ("always", _("_Always")),
            ("never", _("_Never")),
        ]

        def config_changed(radio, value):
            if radio.get_active():
                config.set("plugins", "fingerprint_puid_lookup", value)

        start_value = get_puid_lookup()
        radio = None
        for value, text in options:
            radio = gtk.RadioButton(group=radio, label=text)
            radio.child.set_use_markup(True)
            radio.set_active(value == start_value)
            radio.connect("toggled", config_changed, value)
            puid_box.pack_start(radio)

        box.pack_start(Frame(_("PUID Lookup"), child=puid_box))

        return box
