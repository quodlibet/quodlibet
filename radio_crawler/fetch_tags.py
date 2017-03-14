#!/usr/bin/env python2
# Copyright 2011,2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import multiprocessing

from gi.repository import GLib
from gi.repository import Gst

from util import TagListWrapper, get_cache, get_failed, set_cache, set_failed


PROCESSES = 100
TIMEOUT = 5
NEEDED = ["organization", "audio-codec", "bitrate"]


def get_tags(uri):
    """Returns (uri, tags_dict)"""

    tags = {}
    player = Gst.ElementFactory.make("playbin", "player")
    fakesink = Gst.ElementFactory.make("fakesink", "fakesink")
    fakesink2 = Gst.ElementFactory.make("fakesink", "fakesink")
    player.set_property("audio-sink", fakesink)
    player.set_property("video-sink", fakesink2)
    bus = player.get_bus()
    bus.add_signal_watch()

    ml = GLib.MainLoop()

    def message(bus, message, player):
        if message.type == Gst.MessageType.TAG:
            t = TagListWrapper(message.parse_tag(), merge=True)
            for k in t.keys():
                v = str(t[k])
                if not k.endswith("bitrate") and k in tags and \
                        v not in tags[k]:
                    tags[k].append(v)
                else:
                    tags[k] = [v]

            if "nominal-bitrate" in tags and "bitrate" not in tags:
                tags["bitrate"] = tags["nominal-bitrate"]

            # not everyone sends the codec, so ask the typefind element
            typefind = player.get_by_name("typefind")
            if typefind and typefind.props.caps and "audio-codec" not in tags:
                caps = typefind.props.caps
                if "audio/aac" in caps.to_string():
                    tags["audio-codec"] = ["AAC (Advanced Audio Coding)"]
                elif "audio/mpeg" in caps.to_string():
                    tags["audio-codec"] = ["MPEG 1 Audio, Layer 3 (MP3)"]

            if not set(NEEDED) - set(tags.keys()):
                ml.quit()
        elif message.type == Gst.MessageType.ERROR or \
                message.type == Gst.MessageType.EOS:
            ml.quit()
        elif message.type == Gst.MessageType.BUFFERING:
            percent = message.parse_buffering()
            if percent == 100:
                player.set_state(Gst.State.PLAYING)
            else:
                player.set_state(Gst.State.PAUSED)

    sig = bus.connect("message", message, player)
    player.set_property("uri", uri)
    player.set_state(Gst.State.PLAYING)
    player.get_state(Gst.SECOND)

    GLib.timeout_add(TIMEOUT * 1000, ml.quit)

    try:
        ml.run()
    except:
        pass

    bus.remove_signal_watch()
    bus.disconnect(sig)
    player.set_state(Gst.State.NULL)

    return uri, tags


def get_all_tags(uris):
    """Returns a mapping of uris: tags and a list of failed uris"""

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
    except:
        pass
    finally:
        pool.terminate()
        pool.join()

    return result, failed


def main():
    cache = get_cache()
    failed_uris = get_failed()

    # don't check uris that have enough tags in the cache
    done = set()
    tags = set(NEEDED)
    for key, value in cache.iteritems():
        if not tags - set(value.keys()):
            done.add(key)

    # also don't check failed (to allow multiple partial runs)
    done |= failed_uris

    # get uris for the rest
    uris_todo = set(cache.keys()) - done

    # get tags and replace all results
    new_result, new_failed = get_all_tags(uris_todo)
    for uri, tags in new_result.iteritems():
        if uri in cache:
            cache[uri].update(tags)
        else:
            cache[uri] = tags

    set_failed(failed_uris | set(new_failed))
    set_cache(cache)


if __name__ == "__main__":
    Gst.init(None)
    main()
