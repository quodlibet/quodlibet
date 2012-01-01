# Copyright 2011 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import urllib2
import re

def fetch_difm_urls():
    urls = {"http://www.sky.fm": "/include/menus/skyguest.js",
            "http://www.di.fm": "/menus/diguest.js",
            }

    print "fetching playlists.."

    lists = set()
    for root, url in urls.iteritems():
        print "%s ..." % root
        sock = urllib2.urlopen(root + url)
        data = sock.read()
        reg = re.compile("href=\"(.+?\.pls)\"")
        for match in reg.findall(data):
            if match.startswith("/"):
                match = root + match
            lists.add(match)

    print "%d playlists found." % len(lists)

    print "Extracting stream URLs..."

    final = set()
    for i, url in enumerate(lists):
        print url
        print "%d of %d" % (i + 1, len(lists))

        try: sock = urllib2.urlopen(url)
        except:
            print "error fetching %s" % url
            continue

        data = sock.read()
        values = [l.split("=")[-1] for l in data.splitlines()]
        urls = [l.strip() for l in values if l.startswith("http://")]
        final.update(urls)

    print "%d URLs found." % len(final)

    return final


urls = fetch_difm_urls()
print "writing..."
f = open("uris.txt", "ab")
f.write("\n".join(urls)+"\n")
f.close()
