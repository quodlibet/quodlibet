# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2012 Christoph Reiter
#           2016-23 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from typing import cast

from quodlibet import util
from quodlibet.util.importhelper import load_dir_modules

from ._base import Browser

browsers: list[type[Browser]] = []

BrowserName = str
BrowserKey = int | BrowserName
"""Either the index or the string key of the browser"""

default = None


def init() -> None:
    """Import all browsers from this package and from the user directory.

    After this is called the global `browsers` list will contain all
    classes sorted by priority.

    Can be called multiple times.
    """

    global browsers, default

    # ignore double init (for the test suite)
    if browsers:
        return

    this_dir = util.get_module_dir()
    modules = load_dir_modules(this_dir, package=__package__)

    for browser in modules:
        try:
            browsers.extend(browser.browsers)
        except AttributeError:
            util.print_w("%r doesn't contain any browsers." % browser.__name__)

    def is_browser(klass):
        return isinstance(klass, type) and issubclass(klass, Browser)

    browsers = list(filter(is_browser, browsers))

    if not browsers:
        raise SystemExit("No browsers found!")

    browsers.sort(key=lambda cls: cls.priority)

    try:
        default = get("SearchBar")
    except ValueError as e:
        raise SystemExit("Default browser not found!") from e


def name(browser: Browser) -> BrowserName:
    """Return the name of the browser"""

    return browser.keys[0]


def get(i: BrowserKey) -> type[Browser]:
    """Return a constructor for a browser, either given by number, a string
    of the number, or the name.

    Raises ValueError if the lookup fails.
    """

    try:
        return browsers[int(i)]
    except (IndexError, ValueError, TypeError):
        try:
            return get(index(cast(str, i)))
        except IndexError as e:
            # ValueError will fall through
            raise ValueError(f"{i!r} not found") from e


def index(name: BrowserName) -> int:
    """Return the index of a browser given its name.

    Raises ValueError if the lookup fails.
    """

    name = name.lower()
    for j, browser in enumerate(browsers):
        keys = [k.lower() for k in browser.keys]
        if name in keys:
            return j

    all_keys = (k.lower() for b in browsers for k in b.keys)
    raise ValueError(f"{name!r} browser not found. " f"Try: {' | '.join(all_keys)}")
