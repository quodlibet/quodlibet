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

modules.remove(join(basename(base), "__init__"))
modules.remove(join(basename(base), "audio"))

modules = zip(modules, map(__import__, modules))
_infos = {}
_players = {}
for name, mod in modules:
    for ext in mod.extensions:
        _infos[ext] = mod.info
        _players[ext] = mod.player

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
