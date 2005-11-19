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
    if gst.element_factory_make('musepackdec'): extensions = [".mpc", ".mp+"]
    else: extensions = []

class MPCFile(APEv2File):
    format = "Musepack"
    
    def __init__(self, filename):
        super(MPCFile, self).__init__(filename)

        f = musepack.MPCFile(filename)
        self["~#length"] = int(f.length / 1000)
        try: self["~#bitrate"] = int(f.bitrate)
        except AttributeError: pass
        try:
            track_g = "%+0.2f dB" % (f.gain_radio / 100.0)
            album_g = "%+0.2f dB" % (f.gain_audiophile / 100.0)
            track_p = str(f.peak_radio / 32767.0)
            album_p = str(f.peak_audiophile / 32767.0)
        except AttributeError: pass
        else:
            self["replaygain_track_gain"] = track_g
            self["replaygain_track_peak"] = track_p
            self["replaygain_album_gain"] = album_g
            self["replaygain_album_peak"] = album_p

        self.sanitize(filename)

info = MPCFile
