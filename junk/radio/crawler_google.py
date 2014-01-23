#!/usr/bin/python
# Copyright 2011,2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import urllib2
import simplejson
import urllib
import time
import random
import itertools
import socket
import sys


URIS = "uris.txt"
CRAWL_INDEX = "google_crawl_index.txt"


# use tor to get a new IP if needed
if "--tor" in sys.argv[1:]:
    import socks
    from stem import Signal
    from stem.control import Controller

    socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, "127.0.0.1", 9050)
    old_socket = socket.socket
    socket.socket = socks.socksocket

    def new_id():
        print "new id..."
        # stem doesn't like the socket monkey patching needed for urllib2
        prev = socket.socket
        socket.socket = old_socket
        with Controller.from_port(port=9051) as controller:
            controller.authenticate()
            controller.signal(Signal.NEWNYM)
        socket.socket = prev
    new_id()
else:
    def new_id():
        time.sleep(20)


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
    periods = ["d3", "m", "m3", "y"]
    subfixes = range(256)
    subfixes += "a b c d e f g h i j k l m n o p q r s t u v w x y z".split()

    return list(sorted(list(itertools.product(searches, periods, subfixes))))


def main():
    base_fmt = 'http://ajax.googleapis.com/ajax/services/search/web?' \
        'v=1.0&start=%d&rsz=8&safe=off&filter=0&tbs=qdr:%s&q=%s'

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

            page_start = 0
            while page_start < 64:
                print "page offset: ", page_start
                string_quote = urllib.quote('"%s" %s' % (search, str(index)))
                url = base_fmt % (page_start, period, string_quote)
                request = urllib2.Request(url, None, header)
                response = urllib2.urlopen(request)
                results = simplejson.load(response)

                try:
                    res = results['responseData']['results']
                except TypeError:
                    print "error: " + results['responseDetails']
                    print "waiting 20 seconds..."
                    new_id()
                    continue
                else:
                    print "found: %d uris" % len(res)
                    urls = [e['url'] for e in res]

                    num_new = len(set(urls) - all_urls)
                    if num_new == 0:
                        print "nothing new, skip"
                        break

                    new_urls.update(urls)
                    all_urls.update(urls)

                    page_start += 8
    finally:
        print "writing..."
        with open(URIS, "ab") as f:
            f.write("\n".join(new_urls)+"\n")


if __name__ == "__main__":
    main()
