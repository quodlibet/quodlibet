# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gst

from formats._vorbis import MutagenVCFile

try:
    from mutagen.flac import FLAC
except ImportError:
    FLAC = None
    extensions = []
else:
    try: gst.element_factory_make('flacdec')
    except gst.PluginNotFoundError: extensions = []
    else: extensions = [".flac"]

class FLACFile(MutagenVCFile):
    format = "FLAC"
    MutagenType = FLAC

info = FLACFile
