# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gst
from formats._apev2 import APEv2File

try: import musepack
except ImportError: extensions = []
else:
    if gst.element_factory_make('monkeysdec'): extensions = [".ape"]
    else: extensions = []

class APEFile(APEv2File):
    format = "MonkeysAudio"
    
    def __init__(self, filename):
        f = file(filename)
        if f.read(4) != "MAC ":
            raise IOError("Not an APE file.")
        if f.read(2) > "\x8c\x00":
            raise IOError("MonkeysAudio > 3.97 not supported.")

        super(APEFile, self).__init__(filename)
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

info = APEFile
