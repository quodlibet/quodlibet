# Copyright 2011,2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import threading
import urllib
import urllib2
from xml.dom.minidom import parseString

from gi.repository import GLib


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
            try:
                dom = parseString(xml)
            except:
                error = "xml error"
            else:
                puids = dom.getElementsByTagName("puid")
                if puids and puids[0].hasAttribute("id"):
                    return puids[0].getAttribute("id")

        if error:
            print_w("[fingerprint] MusicDNS lookup failed: " + error)

    def run(self):
        self.__sem.release()
        GLib.timeout_add(self.INTERVAL, self.__inc_sem)

        items = [(s, d) for s, d in self.__fingerprints.iteritems()
                 if "ofa" in d]
        for i, (song, data) in enumerate(items):
            self.__sem.acquire()
            if self.__stopped:
                return

            puid = self.__get_puid(data["ofa"], data["length"])
            if puid:
                data["puid"] = puid

            GLib.idle_add(self.__progress_cb, song,
                float(i + 1) / len(items))

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
