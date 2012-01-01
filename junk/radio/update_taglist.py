# Copyright 2011 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import multiprocessing
import subprocess
import cPickle as pickle
import random
import urllib2
import re


PROCESSES = 75 # 30 is about 1 gig RAM on 64bit
TIMEOUT = 15 # seconds


def get_listener_peak(uri):
    """Returns the listener peak number from shoutcast servers or -1"""

    try:
        request = urllib2.Request(uri, None, {'User-agent': 'Mozilla/4.0'})
        sock = urllib2.urlopen(request, None, TIMEOUT)
        data = sock.read(30 * 1024)

        p = re.compile(r'<.*?>')
        data = p.sub(' ', data).split()
        listener_peak = int(data[data.index("Peak:") + 1])
    except Exception, e:
        return -1
    else:
        return listener_peak


def get_tags(uri):
    import gobject
    import gst
    import signal

    def alarm_handler(*args):
        raise IOError

    signal.signal(signal.SIGALRM, alarm_handler)
    signal.alarm(TIMEOUT)

    tags = {}
    player = gst.element_factory_make("playbin2", "player")
    fakesink = gst.element_factory_make("fakesink", "fakesink")
    fakesink2 = gst.element_factory_make("fakesink", "fakesink")
    player.set_property("audio-sink", fakesink)
    player.set_property("video-sink", fakesink2)
    bus = player.get_bus()
    bus.add_signal_watch()

    ml = gobject.MainLoop()
    sig = None

    def done(player, bus):
        bus.remove_signal_watch()
        bus.disconnect(sig)
        player.set_state(gst.STATE_NULL)
        player.get_state()
        ml.quit()

    def message(bus, message, player):
        if message.type == gst.MESSAGE_TAG:
            t = message.parse_tag()
            for k in t.keys():
                v = t[k]
                if isinstance(v, unicode):
                    v = v.encode("utf-8")
                else:
                    v = str(v)
                if not k.endswith("bitrate") and k in tags and v not in tags[k]:
                    tags[k].append(v)
                else:
                    tags[k] = [v]
            if "minimum-bitrate" in t.keys():
                if "nominal-bitrate" in tags:
                    tags["bitrate"] = tags["nominal-bitrate"]
                done(player, bus)
        elif message.type == gst.MESSAGE_ERROR or message.type == gst.MESSAGE_EOS:
            done(player, bus)
        elif message.type == gst.MESSAGE_BUFFERING:
            percent = message.parse_buffering()
            if percent == 100:
                player.set_state(gst.STATE_PLAYING)
            else:
                player.set_state(gst.STATE_PAUSED)

    sig = bus.connect("message", message, player)
    player.set_property("uri", uri)
    player.set_state(gst.STATE_PLAYING)

    try: ml.run()
    except: pass

    if tags:
        peak = get_listener_peak(uri)
        if peak >= 0:
            tags["~listenerpeak"] = [str(peak)]

    return uri, tags


def get_all_tags(uris):
    random.shuffle(uris)
    result = {}
    failed = []

    try:
        pool = multiprocessing.Pool(PROCESSES)
        for i, (uri, tags) in enumerate(pool.imap_unordered(get_tags, uris)):
            print "%d/%d " % (i+1, len(uris)) + uri + " -> ",
            if tags:
                result[uri] = tags
                print "OK: ", len(tags)
            else:
                print "FAILED"
                failed.append(uri)
    except KeyboardInterrupt:
        pool.terminate()

    pool.close()
    pool.join()

    return result, failed


def dump_taglist(out_fn, in_fn, cache="tag_cache.pickle", tags_whitelist=[],
        val_blacklist=[], tags_needed=[]):
    """Writes all tags to a file in the following format:

    uri=http://bla.com
    key=value
    key2=value2
    key=value3

    Each uri starts a new entry; there are no newlines; multiple values
    get transformed to multiple key=value pairs.

    tags that start with ~ are metadata not retrieved from the stream.
    e.g. ~listenerpeak is the listener peak value from the shoutcast page.
    """

    try:
        result = pickle.load(open(cache, "rb"))
    except (IOError, EOFError):
        result = {}

    uris = set(open(in_fn, "rb").read().splitlines())

    needed = set(tags_needed)
    out = []
    written = 0
    for uri in uris:
        if uri not in result:
            continue
        tags = result[uri]
        if needed - set(tags.keys()):
            continue
        written += 1
        out.append("uri=" + uri)
        for key, values in tags.iteritems():
            if key not in tags_whitelist:
                continue
            for val in values:
                if val in val_blacklist:
                    continue
                out.append(key + "=" + val)

    print "Writing taglist..."
    print written, " stations"
    open(out_fn, "wb").write("\n".join(out))


def update_tag_cache(fn, tags_needed=[], failed_fn="uris_failed.txt",
        cache="tag_cache.pickle"):

    print "Updating tag cache..."

    try:
        result = pickle.load(open(cache, "rb"))
    except(IOError, EOFError):
        result = {}

    # only dump uris in the clean list
    uris = set(open(fn, "rb").read().splitlines())

    # don't check uris that have enough tags in the cache
    done = set()
    tags = set(tags_needed)
    for key, value in result.iteritems():
        if not tags - set(value.keys()):
            done.add(key)

    # also don't check failed (to allow multiple partial runs)
    try: done |= set(open(failed_fn, "rb").read().splitlines())
    except IOError: pass

    uris = list(uris - done)

    # replace all results
    new_result, failed = get_all_tags(uris)
    for uri, tags in new_result.iteritems():
        if uri in result:
            result[uri].update(tags)
        else:
            result[uri] = tags

    # append the failed ones
    open(failed_fn, "ab").write("\n".join(set(failed)))

    # and update the cache
    print "Writing tag cache..."
    pickle.dump(result, open(cache, "wb"))


INPUT_URIS = "uris_clean.txt"
OUTPUT_NAME = "radiolist"

# tags that get written to the final list
tags = ["organization", "location", "genre", "channel-mode",
        "audio-codec", "bitrate", "~listenerpeak"]

# blacklisted values
vbl = ["http://www.shoutcast.com", "http://localhost/", "Default genre",
    "None", "http://", "Unnamed Server", "Unspecified", "N/A"]

# tags needed for station to be written to the final list
needed = ["organization", "audio-codec", "bitrate"]

# check all missing stations
update_tag_cache(INPUT_URIS, tags_needed=needed)

# write out the taglist
dump_taglist(OUTPUT_NAME, INPUT_URIS,
             tags_whitelist=tags, val_blacklist=vbl,
             tags_needed=needed)
