#!/usr/bin/env python2
# Copyright 2011,2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
Takes the cache file and writes a text list parse-able by QL containing
only streams which have enough meta data
"""

from __future__ import print_function

import bz2

from util import get_cache, LISTENERPEAK, LISTENERCURRENT


# tags that get written to the final list if available
TAGS = [
    "organization",
    "location",
    "genre",
    "channel-mode",
    "audio-codec",
    "bitrate",
    LISTENERPEAK,
]

# blacklisted values
VBL = [
    "http://www.shoutcast.com",
    "http://localhost/",
    "Default genre",
    "None",
    "http://",
    "Unnamed Server",
    "Unspecified",
    "N/A",
]

NEEDED = ["organization", "audio-codec", "bitrate"]

STATIONFILE = "radiolist"


def main():
    """Writes all tags to a file in the following format:

    uri=http://bla.com
    key=value
    key2=value2
    key=value3

    Each URI starts a new entry; there are no newlines; multiple values
    get transformed to multiple key=value pairs.

    tags that start with ~ are metadata not retrieved from the stream.
    e.g. ~listenerpeak is the listener peak value from the shoutcast page.
    """

    cache = get_cache()

    needed = set(NEEDED)
    out = []
    written = 0
    for uri, tags in cache.iteritems():
        if needed - set(tags.keys()):
            continue
        written += 1
        # XXX
        uri = str(uri)
        out.append("uri=" + uri)

        # add current to peak, xiph have only current e.g.
        if LISTENERPEAK not in tags:
            if LISTENERCURRENT in tags:
                tags[LISTENERPEAK] = tags[LISTENERCURRENT]
        else:
            tags[LISTENERPEAK].extend(tags.get(LISTENERCURRENT, []))

        # take the larges one
        peaks = tags.get(LISTENERPEAK, [])
        peaks = map(int, peaks)
        if peaks:
            tags[LISTENERPEAK] = [str(max(peaks))]

        for key, values in tags.iteritems():
            if key not in TAGS:
                continue
            for val in values:
                if isinstance(val, unicode):
                    val = val.encode("utf-8")
                if val in VBL:
                    continue
                out.append(key + "=" + val)

    print("Writing taglist...")
    print(written, " stations")
    with open(STATIONFILE, "wb") as h:
        h.write("\n".join(out))

    print("Write compressed version...")
    with open(STATIONFILE + ".bz2", "wb") as h:
        h.write(bz2.compress(open(STATIONFILE, "rb").read(), 9))


if __name__ == "__main__":
    main()
