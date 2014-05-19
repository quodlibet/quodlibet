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

from .util import get_api_key, GateKeeper, get_write_mb_tags


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


Release = collections.namedtuple("Release", ["id", "score", "sources", "tags"])


def parse_acoustid_response(json_data, musicbrainz=True):
    """Get all possible tag combinations including the release ID and score.

    The idea is that for multiple songs the variant for each wins where
    the release ID is present for more songs and if equal
    (one song for example) the score wins.

    Needs meta=releases+recordings+tracks responses.
    """

    VARIOUS_ARTISTS_ARTISTID = "89ad4ac3-39f7-470e-963a-56509c546377"

    releases = []
    for res in json_data.get("results", []):
        score = res["score"]
        for rec in res.get("recordings", []):
            sources = rec["sources"]
            title = rec.get("title", "")
            rec_id = rec["id"]
            artists = [a["name"] for a in rec.get("artists", [])]
            artist_ids = [a["id"] for a in rec.get("artists", [])]

            for release in rec.get("releases", []):
                # release
                id_ = release["id"]
                date = release.get("date", {})
                album = release.get("title", "")
                album_id = release["id"]
                parts = [date.get(k) for k in ["year", "month", "day"]]
                date = "-".join([u"%02d" % p for p in parts if p is not None])

                albumartists = []
                albumartist_ids = []
                for artist in release.get("artists", []):
                    if artist["id"] != VARIOUS_ARTISTS_ARTISTID:
                        albumartists.append(artist["name"])
                        albumartist_ids.append(artist["id"])
                discs = release.get("medium_count", 0)

                # meadium
                medium = release["mediums"][0]
                disc = medium.get("position", 0)
                tracks = medium.get("track_count", 0)

                # track
                track_info = medium["tracks"][0]
                track_id = track_info["id"]
                track = track_info.get("position", 0)

                if disc and discs:
                    discnumber = u"%d/%d" % (disc, discs)
                else:
                    discnumber = u""

                if track and tracks:
                    tracknumber = u"%d/%d" % (track, tracks)
                else:
                    tracknumber = u""

                tags = {
                    "title": title,
                    "artist": "\n".join(artists),
                    "albumartist": "\n".join(albumartists),
                    "date": date,
                    "discnumber": discnumber,
                    "tracknumber": tracknumber,
                    "album": album,
                }

                mb = {
                    "musicbrainz_releasetrackid": track_id,
                    "musicbrainz_trackid": rec_id,
                    "musicbrainz_albumid": album_id,
                    "musicbrainz_albumartistid": "\n".join(albumartist_ids),
                    "musicbrainz_artistid": "\n".join(artist_ids),
                }

                # not that useful, ignore for now
                del mb["musicbrainz_releasetrackid"]

                if musicbrainz:
                    tags.update(mb)

                tags = dict((k, v) for (k, v) in tags.items() if v)
                releases.append(Release(id_, score, sources, tags))

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

        urldata = "&".join([basedata, "meta=releases+recordings+tracks+sources"])
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
                    mb = get_write_mb_tags()
                    releases = parse_acoustid_response(data, musicbrainz=mb)

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
