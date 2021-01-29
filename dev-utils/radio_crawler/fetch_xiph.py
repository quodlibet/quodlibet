#!/usr/bin/env python2
# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from __future__ import print_function

import requests
import re
import urllib
import sys
import cPickle as pickle
from multiprocessing.pool import ThreadPool
import xml.etree.ElementTree as ET

from util import get_cache, set_cache, LISTENERCURRENT

PROCESSES = 50
XIPH_CACHE = "xiph.pickle"


class XiphPlaylist(object):

    def __init__(self, uri, listeners, streams):
        self.uri = uri
        self.listeners = listeners
        self.streams = streams


def parse_playlist(uri):
    r = requests.get(uri)
    # xspf xml isn't escaped.
    # who developed that format? xiph you say? errr....
    reg = re.compile("<location>(.*?)<")
    return uri, reg.findall(r.content)


def parse_playlists(pl_dict):
    result = {}
    try:
        pool = ThreadPool(PROCESSES)
        pfunc = parse_playlist
        args = pl_dict.keys()
        for i, (uri, streams) in enumerate(pool.imap_unordered(pfunc, args)):
            print("%d/%d" % (i + 1, len(args)))
            result[uri] = (pl_dict[uri], streams)
    except Exception as e:
        print(e)
        return {}
    finally:
        pool.terminate()
        pool.join()

    return result


def parse_page(args):
    try:
        genre, page = args
        fmt = "http://dir.xiph.org/by_genre/%s?page=%d"
        uri = fmt % (urllib.quote(genre.encode("utf-8")), page)

        sock = requests.get(uri)
        data = sock.text
        pl_reg = re.compile("(/listen/\d+/listen\.xspf)")
        pls = ["http://dir.xiph.org" + u for u in pl_reg.findall(data)]
        if not pls:
            return genre, page, {}, set()

        list_reg = re.compile("\[(\d+).*?listeners\]")
        listeners = list_reg.findall(data)
        playlists = {}
        for url, count in zip(pls, listeners):
            playlists[url] = int(count)

        reg = re.compile("/by_genre/(.*?)['\"]")
        genres = set(reg.findall(data))

        return genre, page, playlists, genres
    except Exception as e:
        print(e)
        return genre, page, {}, set()


def get_for_genres(genres):
    genres = set(genres)
    playlists = {}
    new_genres = set()

    for page in xrange(5):
        args = []
        for g in genres:
            args.append((g, page))

        try:
            pool = ThreadPool(PROCESSES)
            pfunc = parse_page
            for i, res in enumerate(pool.imap_unordered(pfunc, args)):
                genre, page, pl, found = res
                print("%d/%d" % (i + 1, len(args)))
                playlists.update(pl)
                new_genres |= found
                if not pl:
                    genres.remove(genre)
        except Exception as e:
            print(e)
            return playlists, []
        finally:
            pool.terminate()
            pool.join()

    return playlists, new_genres


def crawl_xiph():
    """List of XiphPlaylist objects"""

    playlists = {}
    done = set()
    genres = set()

    r = requests.get("http://dir.xiph.org/yp.xml")
    elm = ET.fromstring(r.content)
    for e in elm.iter("genre"):
        genres.update(e.text.split())

    while genres:
        print("fetch %d genres" % len(genres))
        new_pl, new_gen = get_for_genres(genres)
        done |= genres
        genres = new_gen - done
        playlists.update(new_pl)

    items = []
    for pl_uri, (listeners, streams) in parse_playlists(playlists).iteritems():
        items.append(XiphPlaylist(pl_uri, listeners, streams))

    return items


def main():

    # crawl and cache
    try:
        with open(XIPH_CACHE, "rb") as h:
            result = pickle.load(h)
    except IOError:
        result = crawl_xiph()
        with open(XIPH_CACHE, "wb") as h:
            pickle.dump(result, h)

    cache = get_cache()

    # add new streams and listeners counts to the cache
    for pl in result:
        for stream in pl.streams:
            if stream not in cache:
                cache[stream] = {}

            if LISTENERCURRENT in cache[stream]:
                cache[stream][LISTENERCURRENT].append(str(pl.listeners))
            else:
                cache[stream][LISTENERCURRENT] = [str(pl.listeners)]

    set_cache(cache)


if __name__ == "__main__":
    main()
