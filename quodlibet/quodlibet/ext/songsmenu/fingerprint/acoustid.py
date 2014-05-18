# Copyright 2011,2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import json
import collections
import threading
import urllib
import urllib2
import Queue
import StringIO
import gzip
from xml.dom.minidom import parseString

from gi.repository import GLib

from .util import get_api_key, GateKeeper


APP_KEY = "C6IduH7D"
gatekeeper = GateKeeper(requests_per_sec=3)


class AcoustidSubmissionThread(threading.Thread):
    URL = "http://api.acoustid.org/v2/submit"
    SONGS_PER_SUBMISSION = 50

    def __init__(self, results, progress_cb, done_cb):
        super(AcoustidSubmissionThread, self).__init__()
        self.__callback = done_cb
        self.__results = results
        self.__stopped = False
        self.__progress_cb = progress_cb
        self.__done = 0
        self.start()

    def __idle(self, func, *args, **kwargs):
        def delayed():
            if self.__stopped:
                return
            func(*args, **kwargs)

        GLib.idle_add(delayed)

    def __send(self, urldata):
        if self.__stopped:
            return

        gatekeeper.wait()

        self.__done += len(urldata)

        basedata = urllib.urlencode({
            "format": "xml",
            "client": APP_KEY,
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
        self.__idle(self.__progress_cb,
                float(self.__done) / len(self.__results))

    def run(self):
        urldata = []
        for i, result in enumerate(self.__results):
            song = result.song
            track = {
                "duration": int(round(result.length / 1000.0)),
                "fingerprint": result.chromaprint,
                "bitrate": song("~#bitrate"),
                "fileformat": song("~format"),
                "mbid": song("musicbrainz_trackid"),
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

        self.__idle(self.__callback)

    def stop(self):
        self.__stopped = True


class LookupResult(object):

    def __init__(self, fresult, releases):
        self.fresult = fresult
        self.releases = releases

    @property
    def song(self):
        return self.fresult.song


Release = collections.namedtuple("Release", ["id", "score", "tags"])


def parse_acoustid_response(json_data):
    """Get all possible tag combinations including the release ID and score.

    The idea is that for multiple songs the variant for each wins where
    the release ID is present for more songs and if equal
    (one song for example) the score wins.

    Needs meta=releases+recordings+compress+tracks responses.
    """

    releases = []

    for res in json_data.get("results", []):
        score = res["score"]
        for rec in res.get("recordings", []):
            title = rec.get("title", "")
            artists = [a["name"] for a in rec.get("artists", [])]
            for release in rec.get("releases", []):
                id_ = release["id"]
                date = release.get("date", {})
                parts = [date.get(k) for k in ["year", "month", "day"]]
                date = "-".join([u"%02d" % p for p in parts if p is not None])

                discs = release["medium_count"]
                medium = release["mediums"][0]
                disc = medium["position"]
                tracks = medium["track_count"]
                track = medium["tracks"][0]["position"]
                album = release.get("title", "")

                tags = {
                    "title": title,
                    "artist": "\n".join(artists),
                    "date": date,
                    "discnumber": u"%d/%d" % (disc, discs),
                    "tracknumber": u"%d/%d" % (track, tracks),
                    "album": album,
                }

                tags = dict((k, v) for (k, v) in tags.items() if v)
                releases.append(Release(id_, score, tags))

    return releases


class AcoustidLookupThread(threading.Thread):
    URL = "http://api.acoustid.org/v2/lookup"

    def __init__(self, progress_cb):
        super(AcoustidLookupThread, self).__init__()
        self.__progress_cb = progress_cb
        self.__queue = Queue.Queue()
        self.__stopped = False
        self.start()

    def put(self, result):
        """Queue a FingerPrintResult"""

        self.__queue.put(result)

    def __idle(self, func, *args, **kwargs):
        def delayed():
            if self.__stopped:
                return
            func(*args, **kwargs)

        GLib.idle_add(delayed)

    def __process(self, result):

        basedata = urllib.urlencode({
            "format": "json",
            "client": APP_KEY,
            "duration": int(round(result.length / 1000.0)),
            "fingerprint": result.chromaprint,
        })

        urldata = "&".join(
            [basedata, "meta=releases+recordings+compress+tracks"])
        obj = StringIO.StringIO()
        gzip.GzipFile(fileobj=obj, mode="wb").write(urldata)
        urldata = obj.getvalue()

        headers = {
            "Content-Encoding": "gzip",
            "Content-type": "application/x-www-form-urlencoded"
        }
        req = urllib2.Request(self.URL, urldata, headers)

        releases = []
        error = ""
        try:
            response = urllib2.urlopen(req)
        except urllib2.HTTPError as e:
            error = "urllib error, code: " + str(e.code)
        except:
            error = "urllib error"
        else:
            try:
                data = json.loads(response.read())
            except ValueError as e:
                error = str(e)
            else:
                if data["status"] == "ok":
                    releases = parse_acoustid_response(data)

        # TODO: propagate error
        error = error
        return LookupResult(result, releases)

    def run(self):
        while 1:
            gatekeeper.wait()
            result = self.__queue.get()
            if self.__stopped:
                return
            self.__idle(self.__progress_cb, self.__process(result))
            self.__queue.task_done()

    def stop(self):
        self.__stopped = True
        self.__queue.put(None)
