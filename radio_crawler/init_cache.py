#!/usr/bin/env python2
# Copyright 2011,2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Initializes the cache from the Google URIs"""


from util import URILIST, set_cache


def main():
    cache = {}
    try:
        with open(URILIST, "rb") as h:
            for uri in h.read().splitlines():
                cache[uri] = {}
    except IOError:
        pass

    set_cache(cache)


if __name__ == "__main__":
    main()
