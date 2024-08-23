# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import re

from senf import fsnative, fsn2text

from quodlibet.util import re_escape


class TagsFromPattern:

    def __init__(self, pattern):
        self.headers = []
        self.slashes = len(pattern) - len(pattern.replace(os.path.sep, "")) + 1
        self.pattern = None
        # patterns look like <tagname> non regexy stuff <tagname> ...
        pieces = re.split(r"(<[A-Za-z0-9~_]+>)", pattern)
        override = {"<tracknumber>": r"\d\d?", "<discnumber>": r"\d\d??"}
        dummies_found = 0
        for i, piece in enumerate(pieces):
            if not piece:
                continue
            if piece[0] + piece[-1] == "<>":
                piece = piece.lower()   # canonicalize to lowercase tag names
                if "~" in piece:
                    dummies_found += 1
                    piece = "<QUOD_LIBET_DUMMY_%d>" % dummies_found
                pieces[i] = "(?P{}{})".format(piece, override.get(piece, ".+?"))
                if "QUOD_LIBET" not in piece:
                    self.headers.append(piece[1:-1])
            else:
                pieces[i] = re_escape(piece)

        # some slight magic to anchor searches "nicely"
        # nicely means if it starts with a <tag>, anchor with a /
        # if it ends with a <tag>, anchor with .xxx$
        # but if it's a <tagnumber>, don't bother as \d+ is sufficient
        # and if it's not a tag, trust the user
        if pattern.startswith("<") and not pattern.startswith("<tracknumber>")\
                and not pattern.startswith("<discnumber>"):
            pieces.insert(0, re_escape(os.path.sep))
        if pattern.endswith(">") and not pattern.endswith("<tracknumber>")\
                and not pattern.endswith("<discnumber>"):
            pieces.append(r"(?:\.[A-Za-z0-9_+]+)$")

        self.pattern = re.compile("".join(pieces))

    def match(self, song):
        return self.match_path(song["~filename"])

    def match_path(self, path):
        assert isinstance(path, fsnative)

        tail = os.path.splitdrive(path)[-1]

        # only match on the last n pieces of a filename, dictated by pattern
        # this means no pattern may effectively cross a /, despite .* doing so
        sep = os.path.sep
        matchon = sep + sep.join(tail.split(sep)[-self.slashes:])
        # work on unicode
        matchon = fsn2text(matchon)
        match = self.pattern.search(matchon)

        # dicts for all!
        if match is None:
            return {}
        else:
            return match.groupdict()
