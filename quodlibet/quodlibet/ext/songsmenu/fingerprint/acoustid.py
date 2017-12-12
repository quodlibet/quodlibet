# -*- coding: utf-8 -*-
# Copyright 2011,2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import json
import collections
import threading
import gzip
from xml.dom.minidom import parseString

from gi.repository import GLib

from quodlibet.util import print_w
from quodlibet.compat import iteritems, urlencode, queue, cBytesIO
from quodlibet.util.urllib import urlopen, Request
from .util import get_api_key, GateKeeper


APP_KEY = "C6IduH7D"
gatekeeper = GateKeeper(requests_per_sec=3)


class AcoustidSubmissionThread(threading.Thread):
    URL = "https://api.acoustid.org/v2/submit"
    SONGS_PER_SUBMISSION = 50
    TIMEOUT = 10.0

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

        basedata = urlencode({
            "format": "xml",
            "client": APP_KEY,
            "user": get_api_key(),
        })

        urldata = "&".join([basedata] + list(map(urlencode, urldata)))
        obj = cBytesIO()
        gzip.GzipFile(fileobj=obj, mode="wb").write(urldata.encode())
        urldata = obj.getvalue()

        headers = {
            "Content-Encoding": "gzip",
            "Content-type": "application/x-www-form-urlencoded"
        }
        req = Request(self.URL, urldata, headers)

        error = None
        try:
            response = urlopen(req, timeout=self.TIMEOUT)
        except EnvironmentError as e:
            error = "urllib error: " + str(e)
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
                "duration": int(round(result.length)),
                "fingerprint": result.chromaprint,
                "bitrate": song("~#bitrate"),
                "fileformat": song("~format"),
                "mbid": song("musicbrainz_trackid"),
                "track": song("title"),
                "artist": song.list("artist"),
                "album": song("album"),
                "albumartist": song("albumartist"),
                "year": song("~year"),
                "trackno": song("~#track"),
                "discno": song("~#disc"),
            }

            tuples = []
            for key, value in iteritems(track):
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

    def __init__(self, fresult, releases, error):
        self.fresult = fresult
        self.releases = releases
        self.error = error

    @property
    def song(self):
        return self.fresult.song


Release = collections.namedtuple(
    "Release", ["id", "score", "sources", "all_sources",
                "medium_count", "tags"])


def parse_acoustid_response(json_data):
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
        all_sources = 0
        recordings = []
        for rec in res.get("recordings", []):
            sources = rec["sources"]
            all_sources += sources
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
                discs = release.get("medium_count", 1)

                # meadium
                medium = release["mediums"][0]
                disc = medium.get("position", 0)
                tracks = medium.get("track_count", 1)

                # track
                track_info = medium["tracks"][0]
                track_id = track_info["id"]
                track = track_info.get("position", 0)
                title = track_info.get("title", "")

                if disc and discs > 1:
                    discnumber = u"%d/%d" % (disc, discs)
                else:
                    discnumber = u""

                if track and tracks > 1:
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

                tags.update(mb)
                recordings.append([id_, score, sources, 0, discs, tags])

        for rec in recordings:
            rec[3] = all_sources
            releases.append(Release(*rec))

    return releases


class AcoustidLookupThread(threading.Thread):
    URL = "https://api.acoustid.org/v2/lookup"
    MAX_SONGS_PER_SUBMISSION = 5
    TIMEOUT = 10.0

    def __init__(self, progress_cb):
        super(AcoustidLookupThread, self).__init__()
        self.__progress_cb = progress_cb
        self.__queue = queue.Queue()
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

    def __process(self, results):
        req_data = []
        req_data.append(urlencode({
            "format": "json",
            "client": APP_KEY,
            "batch": "1",
        }))

        for i, result in enumerate(results):
            postfix = ".%d" % i
            req_data.append(urlencode({
                "duration" + postfix: str(int(round(result.length))),
                "fingerprint" + postfix: result.chromaprint,
            }))

        req_data.append("meta=releases+recordings+tracks+sources")

        urldata = "&".join(req_data)
        obj = cBytesIO()
        gzip.GzipFile(fileobj=obj, mode="wb").write(urldata.encode())
        urldata = obj.getvalue()

        headers = {
            "Content-Encoding": "gzip",
            "Content-type": "application/x-www-form-urlencoded"
        }
        req = Request(self.URL, urldata, headers)

        releases = {}
        error = ""
        try:
            response = urlopen(req, timeout=self.TIMEOUT)
        except EnvironmentError as e:
            error = "urllib error: " + str(e)
        else:
            try:
                data = response.read()
                data = json.loads(data.decode())
            except ValueError as e:
                error = str(e)
            else:
                if data["status"] == "ok":
                    for result_data in data.get("fingerprints", []):
                        if "index" not in result_data:
                            continue
                        index = result_data["index"]
                        releases[index] = parse_acoustid_response(result_data)

        for i, result in enumerate(results):
            yield LookupResult(result, releases.get(str(i), []), error)

    def run(self):
        while 1:
            gatekeeper.wait()
            results = []
            results.append(self.__queue.get())
            while len(results) < self.MAX_SONGS_PER_SUBMISSION:
                # wait a bit to reduce overall request count.
                timeout = 0.5 / len(results)
                try:
                    results.append(self.__queue.get(timeout=timeout))
                except queue.Empty:
                    break

            if self.__stopped:
                return

            for lookup_result in self.__process(results):
                self.__idle(self.__progress_cb, lookup_result)
                self.__queue.task_done()

    def stop(self):
        self.__stopped = True
        self.__queue.put(None)
