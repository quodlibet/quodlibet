# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import sys

from quodlibet import const
from quodlibet import util

from os.path import dirname, basename, isdir, join, splitext
from glob import glob

from quodlibet.browsers._base import Browser

BROWSERS = os.path.join(const.USERDIR, "browsers")

base = dirname(__file__)
self = basename(base)
parent = basename(dirname(base))
modules = [splitext(f)[0] for f in glob(join(base, "[!_]*.py*"))]
modules = ["%s.%s.%s" % (parent, self, basename(m)) for m in modules]

if isdir(BROWSERS):
    sys.path.insert(0, BROWSERS)
    modules.extend([splitext(basename(f))[0] for f in
                    glob(join(BROWSERS, "[!_]*.py*"))])

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
for name in set(modules):
    try: browser = __import__(name, {}, {}, self)
    except Exception, err:
        util.print_exc()
        continue

    try: browsers.extend(browser.browsers)
    except AttributeError:
        print_w(_("%r doesn't contain any browsers.") % browser.__name__)

def is_browser(Kind):
    return isinstance(Kind, type) and issubclass(Kind, Browser)
browsers = filter(is_browser, browsers)

if not browsers:
    raise SystemExit("No browsers found!")

try: sys.path.remove(BROWSERS)
except ValueError: pass

browsers.sort(key=lambda Kind: Kind.priority)

try: sys.modules["browsers.iradio"] = sys.modules["quodlibet.browsers.iradio"]
except KeyError: pass

# Return the name of the ith browser.
def name(i): return browsers[i].__name__

# Return a constructor for a browser, either given by number, a string
# of the number, or the name. Defaults to the first browser if all else
# fails.
def get(i):
    try: return browsers[int(i)]
    except (IndexError, ValueError, TypeError):
        try: return get(index(i))
        except (IndexError, ValueError): return browsers[0]
# Return the index of a browser given its name. Defaults to the first
# browser if all else fails.
def index(i):
    try: return int(i)
    except (ValueError, TypeError):
        try: return map(name, range(len(browsers))).index(i)
        except: return 0

def BrowseLibrary():
    items = []
    for Kind in browsers:
        if Kind.in_menu:
            item = "Browser" + Kind.__name__
            items.append("<menuitem action='%s'/>" % item)
    return "\n".join(items)

def ViewBrowser():
    items = []
    for Kind in browsers:
        item = "View" + Kind.__name__
        items.append("<menuitem action='%s'/>" % item)
    return "\n".join(items)
