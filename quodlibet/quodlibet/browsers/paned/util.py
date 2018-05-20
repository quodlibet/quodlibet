# -*- coding: utf-8 -*-
# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import re

from quodlibet import config
from quodlibet import util
from quodlibet.compat import text_type

from quodlibet.pattern import XMLFromMarkupPattern as XMLFromPattern


class PaneConfig(object):
    """Row pattern format: 'categorize_pattern:display_pattern'

    * display_pattern is optional (fallback: ~#tracks)
    * patterns, tied and normal tags.
    * display patterns can have function prefixes for numerical tags.
    * ':' has to be escaped ('\\:')

    TODO: sort pattern, filter query
    """

    def __init__(self, row_pattern):
        parts = re.split(r"(?<!\\):", row_pattern)
        parts = list(map(lambda p: p.replace(r"\:", ":"), parts))

        is_numeric = lambda s: s[:2] == "~#" and "~" not in s[2:]
        is_pattern = lambda s: '<' in s
        f_round = lambda s: (isinstance(s, float) and "%.2f" % s) or s

        disp = (len(parts) >= 2 and parts[1]) or r"[i](<~#tracks>)[/i]"
        cat = parts[0]

        if is_pattern(cat):
            title = util.pattern(cat, esc=True, markup=True)
            try:
                pc = XMLFromPattern(cat)
            except ValueError:
                pc = XMLFromPattern("")
            tags = pc.tags
            format = pc.format_list
            has_markup = True
        else:
            title = util.tag(cat)
            tags = util.tagsplit(cat)
            has_markup = False
            if is_numeric(cat):

                def format(song):
                    v = text_type(f_round(song(cat)))
                    return [(v, v)]
            else:
                format = lambda song: song.list_separate(cat)

        if is_pattern(disp):
            try:
                pd = XMLFromPattern(disp)
            except ValueError:
                pd = XMLFromPattern("")
            format_display = pd.format
        else:
            if is_numeric(disp):
                format_display = lambda coll: text_type(f_round(coll(disp)))
            else:
                format_display = lambda coll: util.escape(coll.comma(disp))

        self.title = title
        self.tags = set(tags)
        self.format = format
        self.format_display = format_display
        self.has_markup = has_markup

    def __repr__(self):
        return "<%s title=%r tags=%r>" % (
            self.__class__.__name__, self.title, self.tags)


def get_headers():
    # QL <= 2.1 saved the headers tab-separated, but had a space-separated
    # default value, so check for that.
    headers = config.get("browsers", "panes")
    if headers == "~people album":
        return headers.split()
    else:
        return headers.split("\t")


def save_headers(headers):
    headers = "\t".join(headers)
    config.set("browsers", "panes", headers)
