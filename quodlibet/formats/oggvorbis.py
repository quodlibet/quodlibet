# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gst

import mutagen
from formats._vorbis import MutagenVCFile

ogg_formats = []
try: from mutagen.oggvorbis import OggVorbis
except ImportError: OggVorbis = None
else: ogg_formats.append(("vorbisdec", OggVorbis))

try: from mutagen.oggflac import OggFLAC
except ImportError: OggFLAC = None
else: ogg_formats.append(("flacdec", OggFLAC))

try: from mutagen.oggspeex import OggSpeex
except ImportError: OggSpeex = None
else: ogg_formats.append(("speexdec", OggSpeex))

# For historical reasons, the base class is for Ogg Vorbis.
class OggFile(MutagenVCFile):
    format = "Ogg Vorbis"
    MutagenType = OggVorbis

class OggFLACFile(MutagenVCFile):
    format = "Ogg FLAC"
    MutagenType = OggFLAC

class OggSpeexFile(MutagenVCFile):
    format = "Ogg Speex"
    MutagenType = OggSpeex

supported = []

for element, Kind in ogg_formats:
    if Kind is not None:
        try: gst.element_factory_make(element)
        except gst.NoPluginError: pass
        else: supported.append(Kind)

extensions = [".ogg"]
if OggFLAC in supported: extensions.append(".oggflac")
if OggSpeex in supported: extensions.append(".spx")

def info(filename):
    try: audio = mutagen.File(filename)
    except AttributeError:
        audio = OggVorbis(filename)
    if audio is None:
        raise IOError("file type could not be determined")
    else:
        Kind = type(audio)
        for klass in globals().values():
            if Kind is getattr(klass, 'MutagenType', None):
                return klass(filename, audio)
        else:
            raise IOError("file type could not be determined")
