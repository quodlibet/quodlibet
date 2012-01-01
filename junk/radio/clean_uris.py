# Copyright 2011 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import multiprocessing
import re
import urlparse
import time


PROCESSES = 300
TIMEOUT = 30


def fix_uri(uri):
    # some are sub pages of the shoutcast admin panel
    for subfix in [".html", ".php", ".cgi"]:
        if subfix in uri:
            return uri[:uri.rfind("/")+1]

    for s in ["%3Fsid%3D1"]:
        if uri.endswith(s):
            return uri[:-len(s)]

    return uri


def filter_uri(uri):
    for bl in ["streamfinder.com", ".shoutcast.com", ".html", ".php",
               "www.facebook.com", ".pdf", "plus.google.com"]:
        if bl in uri:
            return False

    if not uri:
        return False

    return True


def reverse_lookup(uri):
    import socket
    socket.setdefaulttimeout(TIMEOUT)

    old_uri = uri

    try:
        p = urlparse.urlsplit(uri)
        port, hostname = p.port, p.hostname
    except ValueError:
        return old_uri, uri

    c = 0
    while c < 50:
        try:
            rev = socket.gethostbyaddr(hostname)[0]
        except KeyboardInterrupt:
            return
        except socket.timeout:
            print "timeout"
            time.sleep(0.5)
            c += 1
            continue
        except Exception, e:
            pass
        else:
            rev = rev.rstrip(".")
            if not rev:
                break
            l = list(p)
            l[1] = (port is not None and ":".join([rev, str(port)])) or rev
            uri = urlparse.urlunsplit(l)
        break

    return old_uri, uri


def lookup(uri):
    import socket
    socket.setdefaulttimeout(TIMEOUT)

    try:
        hostname = urlparse.urlsplit(uri).hostname
    except ValueError:
        return uri, None

    addrs = None

    c = 0
    while c < 50:
        try:
            addrs = socket.gethostbyname_ex(hostname)[2]
        except KeyboardInterrupt:
            return
        except socket.timeout:
            print "timeout"
            time.sleep(0.5)
            c += 1
            continue
        except Exception, e:
            pass
        break

    return uri, addrs


def filter_ip(uri):
    # if the hostname is an IP addr
    hostname = urlparse.urlsplit(uri).hostname
    return bool(re.match(r"\b(?:\d{1,3}\.){3}\d{1,3}\b$", hostname))


def validate_uri(uri):
    try: urlparse.urlsplit(uri)
    except ValueError: return False
    else: return True


def uri_has_num(uri):
    hostname = urlparse.urlsplit(uri).hostname
    for n in "1 2 3 4 5 6 7 8 9 0".split():
        if n in hostname:
            return True
    return False


###############################################################################


uris = filter(None, set(open("uris.txt", "rb").read().splitlines()))
uris = filter(validate_uri, uris)

clean = []
ips = []

# get all uris with an IP addr as hostname
for uri in uris:
    if filter_ip(uri):
        ips.append(uri)
    else:
        clean.append(uri)

print "ips: ", len(ips), " nonip: ", len(clean)

###############################################################################
# Look up the IPs of hostnames that look like the IP is encoded in them somehow
# if that is the case for any of the returne IPs, use the first returned IP
###############################################################################

# get all uris that have a number in them
check_ip = filter(uri_has_num, clean)

pool = multiprocessing.Pool(PROCESSES)
try:
    for i, (uri, addrs) in enumerate(pool.imap_unordered(lookup, check_ip)):
        print "%d/%d " % (i+1, len(check_ip))

        if not addrs:
            continue

        not_found = 0
        for addr in addrs:
            for num in addr.split('.'):
                if num not in uri:
                    not_found += 1
                    break

        if not_found == len(addrs):
            continue

        p = urlparse.urlsplit(uri)
        port, hostname = p.port, p.hostname

        l = list(p)
        l[1] = addrs[0] + ((port is not None and (":" + str(port))) or "")
        new_uri = urlparse.urlunsplit(l)

        print uri, " -> ", new_uri

        clean.remove(uri)
        clean.append(new_uri)
except Exception, e:
    pool.terminate()
    print e
    raise SystemExit

###############################################################################
# Reverse lookup, if the hostname doesn't include the IP,
# use it instead of the IP
###############################################################################

pool = multiprocessing.Pool(PROCESSES)
try:
    for i, (ip_uri, uri) in enumerate(pool.imap_unordered(reverse_lookup, ips)):
        print "%d/%d " % (i+1, len(ips))

        if uri == ip_uri:
            clean.append(uri)
            continue

        hostname = urlparse.urlsplit(ip_uri).hostname
        for num in hostname.split('.'):
            if num not in uri:
                print ip_uri + " -> " + uri
                clean.append(uri)
                break
        else:
            # all ip parts are in the uri, better use the IP only
            # example: http://127.0.0.1.someserver.com/
            try: clean.remove(uri)
            except ValueError: pass
            clean.append(ip_uri)

finally:
    pool.terminate()
    print "write uris_clean.txt"
    f = open("uris_clean.txt", "wb")
    f.write("\n".join(sorted(filter(filter_uri, map(fix_uri, set(clean))))))
    f.close()
