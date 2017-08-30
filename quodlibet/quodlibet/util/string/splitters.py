# -*- coding: utf-8 -*-
# Copyright 2004-2009 Joe Wreschnig, Michael Urman, Steven Robertson
#           2011-2017 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import re

from quodlibet.util import re_escape


def split_value(s, splitters=[u"/", u"&", u","]):
    """Splits a string. The first match in 'splitters' is used as the
    separator; subsequent matches are intentionally ignored.
    """

    if not splitters:
        return [s.strip()]
    values = s.split("\n")
    for spl in splitters:
        spl = re.compile(r"\b\s*%s\s*\b" % re_escape(spl), re.UNICODE)
        if not list(filter(spl.search, values)):
            continue
        return [st.strip() for v in values for st in spl.split(v)]
    return values


def find_subtitle(title):
    if isinstance(title, bytes):
        title = title.decode('utf-8', 'replace')
    for pair in [u"[]", u"()", u"~~", u"--", u"\u301c\u301c", u'\uff08\uff09']:
        if pair[0] in title[:-1] and title.endswith(pair[1]):
            r = len(pair[1])
            l = title[0:-r].rindex(pair[0])
            if l:
                subtitle = title[l + len(pair[0]):-r]
                return title[:l].rstrip(), subtitle
    else:
        return title, None


def split_title(s, splitters=["/", "&", ","]):
    title, subtitle = find_subtitle(s)
    return ((title.strip(), split_value(subtitle, splitters))
            if subtitle else (s, []))


__FEATURING = ["feat.", "featuring", "feat", "ft", "ft.", "with", "w/"]
__ORIGINALLY = ["originally by ", " cover"]
# Cache case-insensitive regex searches of the above
__FEAT_REGEX = [re.compile(re_escape(s + " "), re.I) for s in __FEATURING]
__ORIG_REGEX = [re.compile(re_escape(s), re.I) for s in __ORIGINALLY]


def split_people(s, splitters=["/", "&", ","]):
    title, subtitle = find_subtitle(s)
    if not subtitle:
        parts = s.split(" ")
        if len(parts) > 2:
            for feat in __FEATURING:
                try:
                    i = [p.lower() for p in parts].index(feat)
                    orig = " ".join(parts[:i])
                    others = " ".join(parts[i + 1:])
                    return orig, split_value(others, splitters)
                except (ValueError, IndexError):
                    pass
        return s, []
    else:
        old = subtitle
        # TODO: allow multiple substitutions across types, maybe
        for regex in (__FEAT_REGEX + __ORIG_REGEX):
            subtitle = re.sub(regex, "", subtitle, 1)
            if old != subtitle:
                # Only change once
                break
        values = split_value(subtitle, splitters)
        return title.strip(), values


def split_album(s):
    name, disc = find_subtitle(s)
    if not disc:
        parts = s.split(" ")
        if len(parts) > 2:
            lower = parts[-2].lower()
            if "disc" in lower or "disk" in lower:
                return " ".join(parts[:-2]), parts[-1]
        return s, None
    else:
        parts = disc.split()
        if (len(parts) == 2 and
                parts[0].lower() in ["disc", "disk", "cd", "vol", "vol."]):
            try:
                return name, parts[1]
            except IndexError:
                return s, None
        else:
            return s, None
