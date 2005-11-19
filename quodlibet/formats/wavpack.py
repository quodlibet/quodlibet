# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gst
from formats._apev2 import APEv2File

try: import musepack.apev2, ctypes
except: extensions = []
else:
    if gst.element_factory_make('wavpackdec'):
        try: _wavpack = ctypes.cdll.LoadLibrary("libwavpack.so.0")
        except: extensions = []
        else: extensions = [".wv"]
    else: extensions = []

class WavpackFile(APEv2File):
    format = "Wavpack"
    
    def __init__(self, filename):
        super(WavpackFile, self).__init__(filename)
        b = ctypes.create_string_buffer(50)
        f = _wavpack.WavpackOpenFileInput(filename, ctypes.byref(b), 0, 0)
        if not f: raise IOError("Not a valid Wavpack file")
        rate = _wavpack.WavpackGetSampleRate(f)
        samples = _wavpack.WavpackGetNumSamples(f)
        self["~#length"] = samples // rate
        _wavpack.WavpackCloseFile(f)
        self.sanitize(filename)

info = WavpackFile
