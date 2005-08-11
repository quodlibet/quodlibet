# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
from os.path import dirname, basename, isdir, join
from fnmatch import fnmatch

import __builtin__; __builtin__.__dict__.setdefault("_", lambda a: a)

base = dirname(__file__)
if isdir(base):
    from glob import glob
    modules = [f[:-3] for f in glob(join(base, "*.py"))]
else: # zip file
    from zipfile import ZipFile
    z = ZipFile(dirname(base))
    modules = [f[:-3] for f in z.namelist()
               if fnmatch(f, join("browsers", "*.py"))]

modules = [basename(dirname(m))+"."+basename(m) for m in modules]
modules.remove("browsers.__init__")
modules.remove("browsers.base")

browsers = []
for mod in modules:
    mod = __import__(mod, globals(), locals(), "browsers")
    try: browsers.extend(mod.browsers)
    except AttributeError:
        print "W: %s doesn't contain any browsers." % mod.__name__

browsers.sort()

def get(i): return browsers[i][2]

def get_browsers():
    return [(("Browser%s" % b[2].__name__), b[1], b[2])
            for b in browsers if b[3]]
    
def get_view_browsers():
    return [(("View%s" % b[2].__name__), b[1], b[2]) for b in browsers]

def BrowseLibrary():
    items = []
    for action, label, Kind in get_browsers():
        items.append("<menuitem action='%s'/>" % action)
    return "\n".join(items)

def ViewBrowser():
    items = []
    for action, label, Kind in get_view_browsers():
        items.append("<menuitem action='%s'/>" % action)
    return "\n".join(items)
