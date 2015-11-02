# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

import quodlibet
from quodlibet import util
from quodlibet.util.importhelper import load_dir_modules

from ._base import Browser


browsers = []
default = None


def init():
    """Import all browsers from this package and from the user directory.

    After this is called the global `browers` list will contain all
    classes sorted by priority.

    Can be called multiple times.
    """

    global browsers, default

    # ignore double init (for the test suite)
    if browsers:
        return

    this_dir = os.path.dirname(__file__)
    load_pyc = util.is_windows() or util.is_osx()
    modules = load_dir_modules(this_dir,
                               package=__package__,
                               load_compiled=load_pyc)

    user_dir = os.path.join(quodlibet.get_user_dir(), "browsers")
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
    browsers = list(filter(is_browser, browsers))

    if not browsers:
        raise SystemExit("No browsers found!")

    browsers.sort(key=lambda Kind: Kind.priority)

    try:
        default = get("SearchBar")
    except ValueError:
        raise SystemExit("Default browser not found!")


def name(browser):
    """Return the name of the browser"""

    return browser.keys[0]


def get(i):
    """Return a constructor for a browser, either given by number, a string
    of the number, or the name.

    Raises ValueError if the lookup fails.
    """

    try:
        return browsers[int(i)]
    except (IndexError, ValueError, TypeError):
        try:
            return get(index(i))
        except (IndexError, ValueError):
            raise ValueError("%r not found" % i)


def index(name):
    """Return the index of a browser given its name.

    Raises ValueError if the lookup fails.
    """

    name = name.lower()
    for j, browser in enumerate(browsers):
        keys = [k.lower() for k in browser.keys]
        if name in keys:
            return j

    raise ValueError("%r not found" % name)
