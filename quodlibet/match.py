# Copyright 2004 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import time

# True if the object matches any of its REs.
class Union(object):
    def __init__(self, res):
        self.res = res

    def search(self, data):
        for re in self.res:
            if re.search(data): return True
        return False

    def __repr__(self):
        return "<Union %r>" % self.res

# True if the object matches all of its REs.
class Inter(object):
    def __init__(self, res):
        self.res = res

    def search(self, data):
        for re in self.res:
            if not re.search(data): return False
        return True

    def __repr__(self):
        return "<Inter %r>" % self.res

# True if the object doesn't match its RE.
class Neg(object):
    def __init__(self, re):
        self.re = re

    def search(self, data):
        return not self.re.search(data)

    def __repr__(self):
        return "<Neg %r>" % self.re

# Numeric comparisons
class Numcmp(object):
    def __init__(self, tag, op, value):
        if isinstance(tag, unicode): self.tag = tag.encode("utf-8")
        else: self.tag = tag
        self.op = op
        value = value.strip()

        if tag in ["lastplayed", "mtime"]:
            if self.op == ">": self.op = "<"
            elif self.op == "<": self.op = ">"

        if value in ["now"]: value = int(time.time())
        elif value in ["today"]: value = int(time.time() - 24 * 60 * 60)
        else:
            parts = value.split()
            try: value = float(parts[0])
            except ValueError:
                try:
                    hms = map(int, value.split(":"))
                    value = 0
                    for t in hms:
                        value *= 60
                        value += t
                except ValueError:
                    value = 0
            if len(parts) > 1:
                unit = parts[1].strip("s")
                if unit == "minute": value *= 60
                if unit == "hour": value *= 60 * 60
                elif unit == "day": value *= 24 * 60 * 60
                elif unit == "week": value *= 7 * 24 * 60 * 60
                elif unit == "year": value *= 365 * 24 * 60 * 60

                if tag in ["lastplayed", "mtime"]:
                    value = int(time.time() - value)
        self.value = value

    def search(self, data):
        num = data("~#" + self.tag, 0)
        if self.op == ">": return num > self.value
        elif self.op == "=": return num == self.value
        elif self.op == "<": return num < self.value
        else: raise ValueError("Unknown operator %s" % self.op)

    def __repr__(self):
        return "<Numcmp tag=%r, op=%r, value=%d>"%(self.tag,self.op,self.value)

# See if a property of the object matches its RE.
class Tag(object):

    # Shorthand for common tags.
    ABBRS = { "a": "artist",
              "b": "album",
              "v": "version",
              "t": "title",
              "n": "tracknumber",
              "d": "date",
              }
    def __init__(self, names, res):
        self.names = [Tag.ABBRS.get(n.lower(), n.lower()) for n in names]
        self.res = res
        if "*" in self.names:
            self.names.remove("*")
            self.names.extend(["artist", "album", "title", "version",
                               "performer"])
        if not isinstance(self.res, list): self.res = [self.res]

    def search(self, data):
        for name in self.names:
            for re in self.res:
                if re.search(data.get(name, data.get("~"+name, ""))):
                    return True
        return False

    def __repr__(self):
        return ("<Tag names=%r, res=%r>" % (self.names, self.res))
