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
                # The sys module docs say this is where the interactive
                # interpreter stores exceptions, so it should be safe for
                # us to do it -- if we're in the interpreter this does
                # nothing, and if we're not it lets us access them elsewhere.
                # WARNING: Not threadsafe. Don't add files from threads
                # other than the main one.
                import sys
                sys.last_type = sys.last_value = sys.last_traceback = None
                return _infos[ext](filename)
            except:
                print ("W: Error loading %s") % filename
                import sys, traceback
                traceback.print_exc()
                lt, lv, tb = sys.exc_info()
                sys.last_type, sys.last_value, sys.last_traceback = lt, lv, tb
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
