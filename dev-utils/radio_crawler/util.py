#!/usr/bin/python
# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from __future__ import print_function

import os
try:
    from collections import abc
except ImportError:
    import collections as abc  # type: ignore
import urlparse
from collections import namedtuple
import xml.etree.ElementTree as ET
import cPickle as pickle
import socket

import requests
from requests import RequestException
from BeautifulSoup import BeautifulSoup
from gi.repository import Gst


CACHE = "cache.pickle"
FAILED = "failed.txt"
LISTENERPEAK = "~listenerpeak"
LISTENERCURRENT = "~listenercurrent"
URILIST = "uris_clean.txt"


class ParseError(Exception):
    pass


Stream = namedtuple("Stream", "stream, current, peak")


def get_root(uri):
    scheme, netloc, path, query, fragment = urlparse.urlsplit(uri)
    return scheme + "://" + netloc


def parse_shoutcast1(url, timeout=5):
    """A Shoutcast object of raises ParseError"""

    root = get_root(url)

    shoutcast1_status = root + "/7.html"
    headers = {'User-Agent': 'Mozilla/4.0'}
    try:
        r = requests.get(
            shoutcast1_status, headers=headers, timeout=timeout, stream=True)
        if "text" not in r.headers.get("content-type", ""):
            raise ParseError
        r.content
    except (RequestException, socket.timeout):
        raise ParseError
    if r.status_code != 200:
        raise ParseError

    soup = BeautifulSoup(r.content)
    body = soup.find("body")
    if not body:
        raise ParseError

    status_line = body.string
    if status_line is None:
        raise ParseError

    try:
        current, status, peak, max_, unique, bitrate, songtitle = \
            status_line.split(",", 6)
    except ValueError:
        raise ParseError

    try:
        peak = str(int(peak))
        current = str(int(current))
    except ValueError:
        raise ParseError

    return Stream(root, current, peak)


def parse_shoutcast2(url, timeout=5):
    """A list of Shoutcast objects or raises ParseError"""

    root = get_root(url)

    # find all streams
    try:
        r = requests.get(root + "/index.html", timeout=timeout, stream=True)
        if "text" not in r.headers.get("content-type", ""):
            raise ParseError
        r.content
    except (RequestException, socket.timeout):
        raise ParseError
    if r.status_code != 200:
        raise ParseError

    stream_ids = []
    soup = BeautifulSoup(r.content)
    for link in soup.findAll("a"):
        if link.get("href", "").startswith("index.html?sid="):
            stream_ids.append(int(link["href"].split("=")[-1]))

    if not stream_ids:
        raise ParseError

    def get_stream(root, index):
        status = root + "/stats?sid=%d" % index
        try:
            r = requests.get(status, timeout=timeout)
        except (RequestException, socket.timeout):
            raise ParseError
        if r.status_code != 200:
            raise ParseError

        entries = {}
        try:
            elm = ET.fromstring(r.content)
        except ET.ParseError:
            raise ParseError
        for e in elm:
            entries[e.tag.lower()] = e.text

        stream = root + entries["streampath"]
        current = entries["currentlisteners"]
        peak = entries["peaklisteners"]

        peak = str(int(peak))
        current = str(int(current))
        return Stream(stream, current, peak)

    return [get_stream(root, i) for i in stream_ids]


def parse_icecast(url, timeout=5):
    """A list of Shoutcast objects or raises ParseError"""

    root = get_root(url)

    try:
        r = requests.get(root + "/status.xsl", timeout=timeout, stream=True)
        if "text" not in r.headers.get("content-type", ""):
            raise ParseError
        r.content
    except (RequestException, socket.timeout):
        raise ParseError
    if r.status_code != 200:
        raise ParseError

    streams = []
    soup = BeautifulSoup(r.content)
    for c in soup.findAll(lambda t: t.get("class", "") == "newscontent"):
        pl_link = c.find("a")
        if not pl_link:
            raise ParseError
        mount_point = pl_link.get("href", "").rsplit(".", 1)[0]
        if not mount_point:
            raise ParseError
        stream = root + mount_point

        bitrate = current = peak = "0"
        table = c.findAll("table")[-1]
        for row in table.findAll("tr"):
            to_text = lambda tag: "".join(tag.findAll(text=True))
            tds = row.findAll("td")
            if len(tds) != 2:
                raise ParseError
            desc, value = [to_text(td) for td in tds]
            if "Peak Listeners" in desc:
                try:
                    peak = str(int(value))
                except ValueError:
                    raise ParseError
            elif "Current Listeners" in desc:
                try:
                    current = str(int(value))
                except ValueError:
                    raise ParseError
        streams.append(Stream(stream, current, peak))

    return streams


class TagListWrapper(abc.Mapping):
    def __init__(self, taglist, merge=False):
        self._list = taglist
        self._merge = merge

    def __len__(self):
        return self._list.n_tags()

    def __iter__(self):
        for i in xrange(len(self)):
            yield self._list.nth_tag_name(i)

    def __getitem__(self, key):
        if not Gst.tag_exists(key):
            raise KeyError

        values = []
        index = 0
        while 1:
            value = self._list.get_value_index(key, index)
            if value is None:
                break
            values.append(value)
            index += 1

        if not values:
            raise KeyError

        if self._merge:
            try:
                return " - ".join(values)
            except TypeError:
                return values[0]

        return values


def get_cache(path=CACHE):
    print("Load cache",  end="")
    try:
        res = pickle.loads(open(path, "rb").read())
    except(IOError, EOFError):
        res = {}
    print("%d entries" % len(res))
    return res


def set_cache(result, path=CACHE):
    print("Save cache", "%d entries" % len(result))

    tmp = path + ".tmp"
    with open(tmp, "wb") as h:
        h.write(pickle.dumps(result))
        os.fsync(h.fileno())
        os.rename(tmp, path)


def get_failed(path=FAILED):
    try:
        with open(path, "rb") as h:
            return set(filter(None, h.read().splitlines()))
    except IOError:
        return set()


def set_failed(failed_uris, path=FAILED):
    with open(path, "wb") as h:
        h.write("\n".join(sorted(set(failed_uris))))


if __name__ == "__main__":
    print(parse_icecast("http://stream2.streamq.net:8000/"))
    print(parse_shoutcast1("http://radioszerver.hu:8300"))
    print(parse_shoutcast2("http://radio-soundparty.eu:8850/index.html"))
    print(parse_icecast("http://pub1.sky.fm/"))
