#!/usr/bin/python
# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import urlparse
from collections import namedtuple
import xml.etree.ElementTree as ET

import requests
from requests import RequestException
from BeautifulSoup import BeautifulSoup


class ParseError(Exception):
    pass


Stream = namedtuple("Stream", "stream, current, peak, bitrate")


def parse_shoutcast1(url):
    """A Shoutcast object of raises ParseError"""

    scheme, netloc, path, query, fragment = urlparse.urlsplit(url)
    root = scheme + "://" + netloc

    shoutcast1_status = root + "/7.html"
    headers = {'User-Agent': 'Mozilla/4.0'}
    try:
        r = requests.get(shoutcast1_status, headers=headers)
    except RequestException:
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

    return Stream(root, current, peak, bitrate)


def parse_shoutcast2(url):
    """A list of Shoutcast objects or raises ParseError"""

    scheme, netloc, path, query, fragment = urlparse.urlsplit(url)
    root = scheme + "://" + netloc

    # find all streams
    try:
        r = requests.get(root + "/index.html")
    except RequestException:
        raise ParseError
    if r.status_code != 200:
        raise ParseError

    stream_ids = []
    soup = BeautifulSoup(r.content)
    for link in soup.findAll("a"):
        if link["href"].startswith("index.html?sid="):
            stream_ids.append(int(link["href"].split("=")[-1]))

    def get_stream(root, index):
        status = root + "/stats?sid=%d" % index
        try:
            r = requests.get(status)
        except RequestException:
            raise ParseError
        if r.status_code != 200:
            raise ParseError

        entries = {}
        elm = ET.fromstring(r.content)
        for e in elm:
            entries[e.tag.lower()] = e.text

        stream = root + entries["streampath"]
        current = entries["currentlisteners"]
        peak = entries["peaklisteners"]
        bitrate = entries["bitrate"]

        return Stream(stream, current, peak, bitrate)

    return [get_stream(root, i) for i in stream_ids]


def parse_icecast(url):
    """A list of Shoutcast objects or raises ParseError"""

    scheme, netloc, path, query, fragment = urlparse.urlsplit(url)
    root = scheme + "://" + netloc

    try:
        r = requests.get(root + "/status.xsl")
    except RequestException:
        raise ParseError
    if r.status_code != 200:
        raise ParseError

    streams = []
    soup = BeautifulSoup(r.content)
    for c in soup.findAll(lambda t: t.get("class", "") == "newscontent"):
        stream = root + "/" + c.find("h3").string.split("/", 1)[-1]
        if not stream:
            raise ParseError

        bitrate = current = peak = "0"
        table = c.findAll("table")[-1]
        for row in table.findAll("tr"):
            to_text = lambda tag: "".join(tag.findAll(text=True))
            desc, value = [to_text(td) for td in row.findAll("td")]
            if "Peak Listeners" in desc:
                peak = value
            elif "Bitrate" in desc:
                bitrate = value
            elif "Current Listeners" in desc:
                current = value
        streams.append(Stream(stream, current, peak, bitrate))

    return streams


if __name__ == "__main__":
    print parse_shoutcast1("http://radioszerver.hu:8300")
    print parse_shoutcast2("http://radio-soundparty.eu:8850/index.html")
    print parse_icecast("http://pub1.sky.fm/")
