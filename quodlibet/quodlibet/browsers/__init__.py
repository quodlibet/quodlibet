# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import sys

from quodlibet import const
from quodlibet import util
from quodlibet.util.modulescanner import load_dir_modules

from os.path import dirname, basename, isdir, join, splitext
from glob import glob

from quodlibet.browsers._base import Browser

browsers = []

def init():
    global browsers

    this_dir = dirname(__file__)
    load_pyc = os.name == 'nt'
    modules = load_dir_modules(this_dir,
                               package=__package__,
                               load_compiled=load_pyc)

    user_dir = os.path.join(const.USERDIR, "browsers")
    if os.path.isdir(user_dir):
        modules += load_dir_modules(user_dir,
                                    package="quodlibet.fake.browsers",
                                    load_compiled=load_pyc)

    for browser in modules:
        try:
            browsers.extend(browser.browsers)
        except AttributeError:
            print_w("%r doesn't contain any browsers." % browser.__name__)

    def is_browser(Kind):
        return isinstance(Kind, type) and issubclass(Kind, Browser)
    browsers = filter(is_browser, browsers)

    if not browsers:
        raise SystemExit("No browsers found!")

    browsers.sort(key=lambda Kind: Kind.priority)


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
