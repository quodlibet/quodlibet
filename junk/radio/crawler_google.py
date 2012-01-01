# Copyright 2011 Christoph Reiter
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

skip = 0

searches = ["SHOUTcast D.N.A.S. Status", "SHOUTcast Administrator",
            "Current Stream Information"]
periods = ["d3", "m", "m3", "y"]
subfixes = range(256)
subfixes += "a b c d e f g h i j k l m n o p q r s t u v w x y z".split()

base_fmt = 'https://ajax.googleapis.com/ajax/services/search/web?' \
    'v=1.0&start=%d&rsz=8&safe=off&filter=0&tbs=qdr:%s&q=%s'

new_urls = set()
all_urls = set()

f = open("uris.txt", "rb")
all_urls.update(f.read().splitlines())
f.close()

print "# urls: ", len(all_urls)

try:
    gen = sorted(list(itertools.product(searches, periods, subfixes)))
    for i, (search, period, index) in enumerate(gen):

        if i < skip:
            continue

        print "#" * 30
        print i, (search, period, index)

        page_start = 0
        while page_start < 64:
            print "page offset: ", page_start
            string_quote = urllib.quote('"%s" %s' % (search, str(index)))
            url = base_fmt % (page_start, period, string_quote)
            header = {
                'Referer': 'http://code.google.com/p/quodlibet/%d' %
                    random.randint(1, 1000),
                'User-agent': 'Mozilla/%.1f' % random.random()}
            request = urllib2.Request(url, None, header)
            response = urllib2.urlopen(request)
            results = simplejson.load(response)

            try:
                res = results['responseData']['results']
            except TypeError:
                print "error: " + results['responseDetails']
                print "waiting 20 seconds..."
                time.sleep(20)
                continue
            else:
                print "found: %d uris" % len(res)
                urls = [e['url'] for e in res]

                num_new = len(set(urls) - all_urls)
                if num_new == 0:
                    time.sleep(2)
                    print "nothing new, skip"
                    break

                new_urls.update(urls)
                all_urls.update(urls)

                page_start += 8
                time.sleep(2)
finally:
    print "writing..."
    f = open("uris.txt", "ab")
    f.write("\n".join(new_urls)+"\n")
    f.close()
