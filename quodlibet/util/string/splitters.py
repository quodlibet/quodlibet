# Copyright 2004-2009 Joe Wreschnig, Michael Urman, Steven Robertson
#           2011-2018 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import re

from quodlibet.util import re_escape


DEFAULT_TAG_SPLITTERS = ["/", "&", ","]
DEFAULT_SUB_SPLITTERS = ["\u301c\u301c", "\uff08\uff09", "[]", "()", "~~", "--"]


def split_value(s, splitters=DEFAULT_TAG_SPLITTERS):
    """Splits a string. The first match in 'splitters' is used as the
    separator; subsequent matches are intentionally ignored.
    """

    def regex_for(sp):
        return r"{start}\s*{split}\s*{end}".format(
            start=r"(?:\b|(?<=\W))", split=re_escape(sp), end=r"(?:\b|(?=\W))"
        )

    if not splitters:
        return [s.strip()]
    values = s.split("\n")
    for spl in splitters:
        spl = re.compile(regex_for(spl), re.UNICODE)
        if any(spl.search(v) for v in values):
            return [st.strip() for v in values for st in spl.split(v)]
    return values


def find_subtitle(title, delimiters=DEFAULT_SUB_SPLITTERS):
    if isinstance(title, bytes):
        title = title.decode("utf-8", "replace")
    for pair in delimiters:
        if len(pair) == 2 and pair[0] in title[:-1] and title.endswith(pair[1]):
            r = len(pair[1])
            l = title[0:-r].rindex(pair[0])
            if l:
                subtitle = title[l + len(pair[0]) : -r]
                return title[:l].rstrip(), subtitle
    else:
        return title, None


def split_title(
    s, tag_splitters=DEFAULT_TAG_SPLITTERS, sub_splitters=DEFAULT_SUB_SPLITTERS
):
    title, subtitle = find_subtitle(s, sub_splitters)
    return (
        (title.strip(), split_value(subtitle, tag_splitters)) if subtitle else (s, [])
    )


__FEATURING = ["feat.", "featuring", "feat", "ft", "ft.", "with", "w/"]
__ORIGINALLY = ["originally by ", " cover"]
# Cache case-insensitive regex searches of the above
__FEAT_REGEX = [re.compile(re_escape(s + " "), re.I) for s in __FEATURING]
__ORIG_REGEX = [re.compile(re_escape(s), re.I) for s in __ORIGINALLY]


def split_people(
    s, tag_splitters=DEFAULT_TAG_SPLITTERS, sub_splitters=DEFAULT_SUB_SPLITTERS
):
    title, subtitle = find_subtitle(s, sub_splitters)
    if not subtitle:
        parts = s.split(" ")
        if len(parts) > 2:
            for feat in __FEATURING:
                try:
                    i = [p.lower() for p in parts].index(feat)
                    orig = " ".join(parts[:i])
                    others = " ".join(parts[i + 1 :])
                    return orig, split_value(others, tag_splitters)
                except (ValueError, IndexError):
                    pass
        return s, []
    else:
        old = subtitle
        # TODO: allow multiple substitutions across types, maybe
        for regex in __FEAT_REGEX + __ORIG_REGEX:
            subtitle = re.sub(regex, "", subtitle, count=1)
            if old != subtitle:
                # Only change once
                break
        values = split_value(subtitle, tag_splitters)
        return title.strip(), values


def split_album(s, sub_splitters=DEFAULT_SUB_SPLITTERS):
    name, disc = find_subtitle(s, sub_splitters)
    if not disc:
        parts = s.split(" ")
        if len(parts) > 2:
            lower = parts[-2].lower()
            if "disc" in lower or "disk" in lower:
                return " ".join(parts[:-2]), parts[-1]
        return s, None
    else:
        parts = disc.split()
        if len(parts) == 2 and parts[0].lower() in [
            "disc",
            "disk",
            "cd",
            "vol",
            "vol.",
        ]:
            try:
                return name, parts[1]
            except IndexError:
                return s, None
        else:
            return s, None


def split_genre(s: str, tag_splitters: Iterable[str] = DEFAULT_TAG_SPLITTERS) -> List[str]:
    """Splits a single genre tag into multiple genre tags
    """
    valid_split_chars = []
    for char in tag_splitters:
        if char in s:
            valid_split_chars.append(char)
    if not valid_split_chars:
        return [s]
    splitchar = valid_split_chars[-1]
    # Reverses the order of DEFAULT_TAG_SPLITTERS
    # Because Genre0/Genre1, Genre2 should be split on ,
    return  [genre.strip() for genre in s.split(splitchar)]
