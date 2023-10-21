#!/usr/bin/env python2
# Copyright 2011,2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
Loads and parses shoutcast/icecast pages and also adds new stream uris.
"""

from multiprocessing import Pool
import traceback

from util import (parse_shoutcast1, parse_shoutcast2, parse_icecast,
                  ParseError, LISTENERPEAK, LISTENERCURRENT, get_root,
                  get_cache, set_cache, get_failed)


PROCESSES = 20
PARSE_FAILED = "cast_failed.txt"


def get_parse_failed(path=PARSE_FAILED):
    try:
        with open(path, "rb") as h:
            return set(filter(None, h.read().splitlines()))
    except IOError:
        return set()


def set_parse_failed(failed_uris, path=PARSE_FAILED):
    with open(path, "wb") as h:
        h.write("\n".join(sorted(set(failed_uris))))


def fetch_stream_infos(uri):
    """Returns a list of Stream objects (can be empty)"""

    try:
        return uri, [parse_shoutcast1(uri)]
    except ParseError:
        pass
    except Exception:
        print(uri)
        traceback.print_exc()
        raise

    try:
        return uri, parse_icecast(uri)
    except ParseError:
        pass
    except Exception:
        print(uri)
        traceback.print_exc()
        raise

    try:
        return uri, parse_shoutcast2(uri)
    except ParseError:
        pass
    except Exception:
        print(uri)
        traceback.print_exc()
        raise

    return uri, []


def main():
    cache = get_cache()
    failed_uris = get_failed()
    parse_failed_uris = get_parse_failed()

    uris = cache.keys()

    peak_missing = [uri for uri in uris if LISTENERPEAK not in cache[uri]]
    peak_missing = set(peak_missing) - failed_uris

    # XXX: fetch_stream_infos is the same for each root url
    peak_missing = {get_root(uri) for uri in peak_missing}
    peak_missing = set(peak_missing) - parse_failed_uris
    

    pool = Pool(PROCESSES)
    try:
        pfunc = fetch_stream_infos
        for i, res in enumerate(pool.imap_unordered(pfunc, peak_missing)):
            uri, streams = res

            # save all 1000
            if (i+1) % 1000 == 0:
                set_cache(cache)

            print("%d/%d " % (i+1, len(peak_missing)) + uri + " -> ", end="")
            print("%d new streams" % len(streams))

            if not streams:
                parse_failed_uris.add(uri)

            # add new found uris to cache + listener count
            for stream in streams:
                peak = str(int(stream.peak))
                current = str(int(stream.current))
                uri = stream.stream

                if uri not in cache:
                    cache[uri] = {}

                if LISTENERPEAK in cache[uri]:
                    cache[uri][LISTENERPEAK].append(peak)
                else:
                    cache[uri][LISTENERPEAK] = [peak]

                if LISTENERCURRENT in cache[uri]:
                    cache[uri][LISTENERCURRENT].append(current)
                else:
                    cache[uri][LISTENERCURRENT] = [current]

    except Exception as e:
        print(e)
    finally:
        set_parse_failed(parse_failed_uris)
        set_cache(cache)
        pool.terminate()
        pool.join()

if __name__ == "__main__":
    main()
