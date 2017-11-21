#!/usr/bin/env python2
# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import re
import requests

from util import get_cache, set_cache


def get_pls(uri):
    r = requests.get(uri)
    return re.findall("File\d*=(.*)", r.text)


def main():
    uris = []
    r = requests.get("https://somafm.com/listen/")
    playlists = re.findall('[^"\']*?.pls', r.text)
    for i, pls in enumerate(playlists):
        print "%d/%d" % (i + 1, len(playlists))
        uris.extend(get_pls(pls))

    cache = get_cache()
    for uri in uris:
        if uri not in cache:
            cache[uri] = {}
    set_cache(cache)


if __name__ == "__main__":
    main()
