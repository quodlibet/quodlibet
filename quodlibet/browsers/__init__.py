# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import sys
import const
from os.path import dirname, basename, isdir, join
from glob import glob

import __builtin__; __builtin__.__dict__.setdefault("_", lambda a: a)

base = dirname(__file__)
self = basename(base)
modules = [f[:-3] for f in glob(join(base, "[!_]*.py"))]
modules = ["%s.%s" % (self, basename(m)) for m in modules]

if isdir(const.BROWSERS):
    sys.path.insert(0, const.BROWSERS)
    modules.extend([basename(f)[:-3] for f in
                    glob(join(const.BROWSERS, "[!_]*.py"))])

# Browsers are declared and stored as a magic 4-tuple. The first element is
# the sort order (built-in browsers are numbered with integers). The second
# element is the label for the browser (should be marked for translation).
# The third is the constructor for the class. The last is a boolean
# indicating whether it should appear in the "Browse Library" menu (EmptyBar
# and PlaylistBar are useless there, for example).
#
# Browser-tuples are stored as a list in <mod>.browsers.
#
# FIXME: Replace that crap with something sane.

browsers = []
for name in modules:
    browser = __import__(name, globals(), locals(), self)
    try: browsers.extend(browser.browsers)
    except AttributeError:
        print "W: %s doesn't contain any browsers." % browser.__name__
if not browsers:
    raise SystemExit("No browsers found!")

try: sys.path.remove(const.BROWSERS)
except ValueError: pass

browsers.sort()

# Return the name of the ith browser.
def name(i): return browsers[i][2].__name__

# Return a constructor for a browser, either given by number, a string
# of the number, or the name. FIXME: String-of-number can go away after 0.13.
# Defaults to the first browser if all else fails.
def get(i):
    try: return browsers[int(i)][2]
    except (IndexError, ValueError, TypeError):
        try: return get(index(i))
        except (IndexError, ValueError): return browsers[0][2]
# Return the index of a browser given its name. FIXME: String-of-number can
# go away after 0.13. Defaults to the first browser if all else fails.
def index(i):
    try: return int(i)
    except (ValueError, TypeError):
        try: return map(name, range(len(browsers))).index(i)
        except: return 0

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
