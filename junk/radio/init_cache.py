#!/usr/bin/python
# Copyright 2011,2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

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
