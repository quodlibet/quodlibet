#!/usr/bin/env python2
# Copyright 2011,2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import urllib2
import urllib
import random
import itertools

from BeautifulSoup import BeautifulSoup, SoupStrainer


URIS = "uris.txt"
CRAWL_INDEX = "bing_crawl_index.txt"


def get_crawl_index():
    try:
        return int(open(CRAWL_INDEX, "rb").read())
    except IOError:
        return 0


def set_crawl_index(value):
    with open(CRAWL_INDEX, "wb") as h:
        h.write(str(value))


def compute_all_search_combinations():
    searches = ["SHOUTcast D.N.A.S. Status", "SHOUTcast Administrator",
                "Current Stream Information"]
    periods = ["0", "1", "2", "3"]
    subfixes = range(256)
    subfixes += "a b c d e f g h i j k l m n o p q r s t u v w x y z".split()

    return list(sorted(list(itertools.product(searches, periods, subfixes))))


def main():
    base_fmt = ("http://www.bing.com/search?q=%s&first=%d&filters="
                "ex1%%253a%%22ez%s%%22")

    new_urls = set()
    all_urls = set()

    try:
        with open(URIS, "rb") as f:
            all_urls.update(f.read().splitlines())
    except IOError:
        pass

    print "# urls: ", len(all_urls)

    try:
        skip = get_crawl_index()
        gen = compute_all_search_combinations()
        for i, (search, period, index) in enumerate(gen):

            if i < skip:
                continue
            set_crawl_index(i - 1)

            print "#" * 30
            print i, len(gen), (search, period, index)

            header = {
                'Referer': 'http://google.com/p/%d' % random.randint(1, 1000),
                'User-agent': 'Mozilla/%.1f' % random.random()
            }

            page_start = 1
            notfound = 0
            while page_start < 200:
                print "page offset: ", page_start
                string_quote = urllib.quote('"%s" %s' % (search, str(index)))
                url = base_fmt % (string_quote, page_start, period)
                request = urllib2.Request(url, None, header)
                response = urllib2.urlopen(request)

                urls = []
                links = SoupStrainer('a')
                for a in BeautifulSoup(response.read(), parseOnlyThese=links):
                    for k, v in a.attrs:
                        if k == "href":
                            try:
                                v = str(v)
                            except:
                                continue
                            if not v.startswith("http"):
                                continue
                            if ".microsofttranslator.com" in v:
                                continue
                            if ".microsoft.com" in v:
                                continue
                            urls.append(v)

                print set(urls) - all_urls
                num_new = len(set(urls) - all_urls)
                if num_new == 0:
                    notfound += 1
                    if notfound > 1:
                        print "nothing new, skip"
                        break
                else:
                    notfound = 0

                new_urls.update(urls)
                all_urls.update(urls)

                page_start += 10
    finally:
        print "writing..."
        with open(URIS, "ab") as f:
            f.write("\n".join(new_urls)+"\n")


if __name__ == "__main__":
    main()
