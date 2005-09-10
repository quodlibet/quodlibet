# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
from os.path import dirname, basename, isdir, join

base = dirname(__file__)
if isdir(base):
    from glob import glob
    modules = [f[:-3] for f in glob(join(base, "*.py"))]
else: # zip file
    from zipfile import ZipFile
    z = ZipFile(dirname(base))
    modules = [f[:-3] for f in z.namelist() if
               (f.endswith(".py") and f.startswith("formats" + os.sep))]

modules = [join(basename(dirname(m)), basename(m)) for m in modules]

map(modules.remove, filter(lambda f: basename(f).startswith("_"), modules))

modules = zip(modules, map(__import__, modules))
_infos = {}
for name, mod in modules:
    for ext in mod.extensions:
        _infos[ext] = mod.info

def MusicFile(filename):
    for ext in _infos.keys():
        if filename.lower().endswith(ext):
            try:
                return _infos[ext](filename)
            except:
                print ("W: Error loading %s") % filename
                import traceback
                traceback.print_exc()
                return None
    else: return None

def supported(song): return type(song) in _infos.values()

def filter(filename):
    for ext in _infos.keys():
        if filename.lower().endswith(ext): return True
    return False

# Tags to display in the "Add Tag" dialogs
USEFUL_TAGS = (
    # Ogg Vorbis spec tags
    "title version album tracknumber artist genre performer copyright "
    "license organization description location contact isrc date "

    # Other tags we like
    "arranger author composer conductor lyricist discnumber labelid part "
    "website language bpm"
    ).split()

MACHINE_TAGS = (
    "musicbrainz_trackid replaygain_album_peak replaygain_track_peak "
    "replaygain_track_gain replaygain_album_gain"
    ).split()
