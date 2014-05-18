# Copyright 2011,2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import threading
import multiprocessing

from gi.repository import Gst, GLib, GObject


class FingerPrintResult(object):

    def __init__(self, song, chromaprint, length):
        self.song = song
        self.chromaprint = chromaprint
        self.length = length


class FingerPrintPipeline(threading.Thread):
    def __init__(self, pool, song):
        super(FingerPrintPipeline, self).__init__()
        self.daemon = True

        self.__pool = pool
        self.__song = song
        self.__cv = threading.Condition()
        self.__shutdown = False
        self.__fingerprints = {}
        self.__todo = []

        self.start()

    def run(self):
        # pipeline
        pipe = Gst.Pipeline()

        # decode part
        filesrc = Gst.ElementFactory.make("filesrc", None)
        pipe.add(filesrc)

        decode = Gst.ElementFactory.make("decodebin", None)
        pipe.add(decode)
        Gst.Element.link(filesrc, decode)

        # convert to right format
        convert = Gst.ElementFactory.make("audioconvert", None)
        resample = Gst.ElementFactory.make("audioresample", None)
        pipe.add(convert)
        pipe.add(resample)
        Gst.Element.link(convert, resample)

        # ffdec_mp3 got disabled in gstreamer
        # (for a reason they don't remember), reenable it..
        # http://cgit.freedesktop.org/gstreamer/gst-ffmpeg/commit/
        # ?id=2de5aaf22d6762450857d644e815d858bc0cce65
        ffdec_mp3 = Gst.ElementFactory.find("ffdec_mp3")
        if ffdec_mp3:
            ffdec_mp3.set_rank(Gst.Rank.MARGINAL)

        # decodebin creates pad, we link it
        decode.connect_object("pad-added", self.__new_decoded_pad, convert)
        decode.connect("autoplug-sort", self.__sort_decoders)

        chroma_src = resample

        chroma = Gst.ElementFactory.make("chromaprint", None)
        fake2 = Gst.ElementFactory.make("fakesink", None)
        pipe.add(chroma)
        pipe.add(fake2)

        Gst.Element.link(chroma_src, chroma)
        Gst.Element.link(chroma, fake2)
        self.__todo.append(chroma)

        filesrc.set_property("location", self.__song["~filename"])

        # bus
        bus = pipe.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("sync-message", self.__bus_message, chroma)

        # get it started
        self.__cv.acquire()
        pipe.set_state(Gst.State.PLAYING)

        result = pipe.get_state(timeout=Gst.SECOND / 2)[0]
        if result == Gst.StateChangeReturn.FAILURE:
            # something failed, error message kicks in before, so check
            # for shutdown
            if not self.__shutdown:
                self.__shutdown = True
                GLib.idle_add(self.__pool._callback, self.__song,
                    None, "Error", self)
        elif not self.__shutdown:
            # GStreamer probably knows song durations better than we do.
            # (and it's more precise for PUID lookup)
            # In case this fails, we insert the mutagen value
            # (this only works in active playing state)
            ok, d = pipe.query_duration(Gst.Format.TIME)
            if ok:
                self.__fingerprints["length"] = d / Gst.MSECOND
            else:
                self.__fingerprints["length"] = self.__song("~#length") * 1000

            self.__cv.wait()
        self.__cv.release()

        # clean up
        bus.remove_signal_watch()
        pipe.set_state(Gst.State.NULL)

        # we need to make sure the state change has finished, before
        # we can return and hand it over to the python GC
        pipe.get_state(timeout=Gst.SECOND / 2)

    def stop(self):
        self.__shutdown = True
        self.__cv.acquire()
        self.__cv.notify()
        self.__cv.release()

    def __sort_decoders(self, decode, pad, caps, factories):
        # mad is the default decoder with GST_RANK_SECONDARY
        # flump3dec also is GST_RANK_SECONDARY, is slower than mad,
        # but wins because of its name, ffdec_mp3 is faster but had some
        # stability problems (which all seem resolved by now and we call
        # this >= 0.10.31 anyway). Finally there is mpg123
        # (http://gst.homeunix.net/) which is even faster but not in the
        # GStreamer core (FIXME: re-evaluate if it gets merged)
        #
        # Example (atom CPU) 248 sec song:
        #   mpg123: 3.5s / ffdec_mp3: 5.5s / mad: 7.2s / flump3dec: 13.3s

        def set_prio(x):
            i, f = x
            i = {
                "mad": -1,
                "ffdec_mp3": -2,
                "mpg123audiodec": -3
            }.get(f.get_name(), i)
            return (i, f)

        return zip(*sorted(map(set_prio, enumerate(factories))))[1]

    def __new_decoded_pad(self, convert, pad, *args):
        pad.link(convert.get_static_pad("sink"))

    def __bus_message(self, bus, message, chroma):
        error = None
        if message.type == Gst.MessageType.TAG:
            tags = message.parse_tag()

            ok, value = tags.get_string("chromaprint-fingerprint")
            if ok:
                if chroma in self.__todo:
                    self.__todo.remove(chroma)
                self.__fingerprints["chromaprint"] = value
        elif message.type == Gst.MessageType.EOS:
            error = "EOS"
        elif message.type == Gst.MessageType.ERROR:
            error = str(message.parse_error()[0])

        if not self.__shutdown and (not self.__todo or error):
            GLib.idle_add(self.__pool._callback, self.__song,
                self.__fingerprints, error, self)
            self.__shutdown = True
            self.__cv.acquire()
            self.__cv.notify()
            self.__cv.release()


class FingerPrintThreadPool(GObject.GObject):
    __gsignals__ = {
        # FingerPrintResult
        "fingerprint-done": (
            GObject.SignalFlags.RUN_LAST, None, (object,)),
        # AudioFile
        "fingerprint-started": (
            GObject.SignalFlags.RUN_LAST, None, (object,)),
        # AudioFile, str
        "fingerprint-error": (
            GObject.SignalFlags.RUN_LAST, None, (object, object)),
        }

    def __init__(self, max_workers=None):
        super(FingerPrintThreadPool, self).__init__()
        self.__threads = []
        self.__queued = []
        if max_workers is None:
            max_workers = int(multiprocessing.cpu_count() * 1.5)
        self.__max_workers = max_workers
        self.__stopped = False

    def push(self, song):
        self.__stopped = False
        if len(self.__threads) < self.__max_workers:
            self.__threads.append(FingerPrintPipeline(self, song))
            self.emit("fingerprint-started", song)
        else:
            self.__queued.append(song)

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
        if self.__stopped:
            return
        if not error:
            chromaprint = result.get("chromaprint")
            res = FingerPrintResult(song, chromaprint, result["length"])
            self.emit("fingerprint-done", res)
        else:
            self.emit("fingerprint-error", song, error)
        if self.__queued:
            song = self.__queued.pop(0)
            self.__threads.append(FingerPrintPipeline(self, song))
            self.emit("fingerprint-started", song)
