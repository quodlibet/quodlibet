# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gst
from formats._audio import AudioFile

try: import musepack.apev2, ctypes
except: extensions = []
else:
    if gst.element_factory_make('wavpackdec'):
        try: _wavpack = ctypes.cdll.LoadLibrary("libwavpack.so.0")
        except: extensions = []
        else: extensions = [".wv"]
    else: extensions = []

class WavpackFile(AudioFile):
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

    format = "Wavpack"
    
    def __init__(self, filename):
        tag = musepack.APETag(filename)
        for key, value in tag:
            key = self.TRANS.get(key.lower(), key.lower())
            if (value.kind == musepack.apev2.TEXT and
                key not in self.IGNORE):
                self[key] = "\n".join(list(value))


        b = ctypes.create_string_buffer(50)
        f = _wavpack.WavpackOpenFileInput(filename, ctypes.byref(b), 0, 0)
        if not f: raise IOError("Not a valid Wavpack file")
        rate = _wavpack.WavpackGetSampleRate(f)
        samples = _wavpack.WavpackGetNumSamples(f)
        self["~#length"] = samples // rate
        _wavpack.WavpackCloseFile(f)
        self.sanitize(filename)

    def can_change(self, key=None):
        if key is None: return True
        else: return (AudioFile.can_change(self, key) and
                      key not in self.IGNORE)

    def write(self):
        import musepack
        tag = musepack.APETag(self['~filename'])

        keys = tag.keys()
        for key in keys:
            # remove any text keys we read in
            value = tag[key]
            if (value.kind == musepack.apev2.TEXT and key not in self.IGNORE):
                del(tag[key])
        for key in self.realkeys():
            if key in self.IGNORE: continue
            value = self[key]
            key = self.SNART.get(key, key)
            if key in ["isrc", "isbn", "ean/upc"]: key = key.upper()
            else: key = key.title()
            tag[key] = value.split("\n")
        tag.write()
        self.sanitize()

info = WavpackFile
