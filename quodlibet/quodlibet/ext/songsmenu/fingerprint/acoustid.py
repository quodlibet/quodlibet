# Copyright 2011,2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import threading
import urllib
import urllib2
import StringIO
import gzip
from xml.dom.minidom import parseString

from gi.repository import GLib

from quodlibet import config


def get_api_key():
    return config.get("plugins", "fingerprint_acoustid_api_key", "")


class AcoustidSubmissionThread(threading.Thread):
    INTERVAL = 1500
    URL = "http://api.acoustid.org/v2/submit"
    APP_KEY = "C6IduH7D"
    SONGS_PER_SUBMISSION = 50 # be gentle :)

    def __init__(self, fingerprints, invalid, progress_cb, callback):
        super(AcoustidSubmissionThread, self).__init__()
        self.__callback = callback
        self.__fingerprints = fingerprints
        self.__invalid = invalid
        self.__stopped = False
        self.__progress_cb = progress_cb
        self.__sem = threading.Semaphore()
        self.__done = 0
        self.start()

    def __send(self, urldata):
        self.__sem.acquire()
        if self.__stopped:
            return

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
            try:
                dom = parseString(xml)
            except:
                error = "xml error"
            else:
                status = dom.getElementsByTagName("status")
                if not status or not status[0].childNodes or not \
                    status[0].childNodes[0].nodeValue == "ok":
                    error = "response status error"

        if error:
            print_w("[fingerprint] Submission failed: " + error)

        # emit progress
        GLib.idle_add(self.__progress_cb,
                float(self.__done) / len(self.__fingerprints))

    def run(self):
        self.__sem.release()
        GLib.timeout_add(self.INTERVAL, self.__inc_sem)

        urldata = []
        for i, (song, data) in enumerate(self.__fingerprints.iteritems()):
            if song in self.__invalid:
                continue

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
                if not value:
                    continue
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

            if self.__stopped:
                return

        if urldata:
            self.__send(urldata)

        GLib.idle_add(self.__callback, self)

        # stop sem increment
        self.__stopped = True

    def __inc_sem(self):
        self.__sem.release()
        # repeat increment until stopped
        return not self.__stopped

    def stop(self):
        self.__stopped = True
        self.__sem.release()
