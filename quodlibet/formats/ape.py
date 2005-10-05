# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gst
from formats._audio import AudioFile

try: import musepack
except ImportError: extensions = []
else:
    if gst.element_factory_make('monkeysdec'): extensions = [".ape"]
    else: extensions = []

class APEFile(AudioFile):
    # Map APE names to QL names. APE tags are also usually capitalized.
    # Also blacklist a number of tags.
    IGNORE = ["file", "index", "introplay", "dummy",
              "replaygain_track_peak", "replaygain_album_peak",
              "replaygain_track_gain", "replaygain_album_gain"]
    TRANS = { "subtitle": "version",
              "track": "tracknumber",
              "catalog": "labelid",
              "record location": "location"
              }
    SNART = dict([(v, k) for k, v in TRANS.iteritems()])
    
    def __init__(self, filename):
        if file(filename).read(4) != "MAC ":
            raise IOError("Not an APE file.")
        if file(filename).read(2) > "\x8c\x00":
            raise IOError("MonkeysAudio > 3.97 not supported.")

        tag = musepack.APETag(filename)
        for key, value in tag:
            key = APEFile.TRANS.get(key.lower(), key.lower())
            if (value.kind == musepack.apev2.TEXT and
                key not in APEFile.IGNORE):
                self[key] = "\n".join(list(value))

        bin = gst.Pipeline()
        src = gst.element_factory_make('filesrc')
        src.set_property('location', filename)
        dec = gst.element_factory_make('monkeysdec')
        sink = gst.element_factory_make('fakesink')
        gst.element_link_many(src, dec, sink)
        bin.add_many(src, dec, sink)

        bin.set_state(gst.STATE_PLAYING)
        def found_tags(pad, args):
            caps = pad.get_negotiated_caps()
            if not caps: return
            length =  pad.get_peer().query(gst.QUERY_TOTAL, gst.FORMAT_TIME)
            self["~#length"] = length / gst.SECOND
        sink.get_pad("sink").connect('notify::caps', found_tags)

        while (bin.get_state() > gst.STATE_READY and "~#length" not in self):
            bin.iterate()
        self["~#bitrate"] = 0
        self.sanitize(filename)

    def can_change(self, key = None):
        if key is None: return True
        else: return (AudioFile.can_change(self, key) and
                      key not in APEFile.IGNORE)

    def write(self):
        import musepack
        tag = musepack.APETag(self['~filename'])

        keys = tag.keys()
        for key in keys:
            # remove any text keys we read in
            value = tag[key]
            if (value.kind == musepack.apev2.TEXT and
                key not in APEFile.IGNORE):
                del(tag[key])
        for key in self.realkeys():
            value = self[key]
            key = APEFile.SNART.get(key, key)
            if key in ["isrc", "isbn", "ean/upc"]: key = key.upper()
            else: key = key.title()
            tag[key] = value.split("\n")
        tag.write()
        self.sanitize()

info = APEFile
