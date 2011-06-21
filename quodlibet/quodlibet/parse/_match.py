# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import time

TIME_KEYS = ["added", "mtime", "lastplayed", "laststarted"]
SIZE_KEYS = ["filesize"]

# True if the object matches any of its REs.
class Union(object):
    def __init__(self, res):
        self.__res = res

    def search(self, data):
        for re in self.__res:
            if re.search(data): return True
        return False

    def __repr__(self):
        return "<Union %r>" % self.__res

    def __or__(self, other):
        if isinstance(other, Union):
            return Union(self.__res + other.__res)
        else: return Union(self.__res + [other])
    __ror__ = __or__

    def __and__(self, other):
        if not isinstance(other, Inter):
            return Inter([self, other])
        return NotImplemented

# True if the object matches all of its REs.
class Inter(object):
    def __init__(self, res):
        self.__res = res

    def search(self, data):
        for re in self.__res:
            if not re.search(data): return False
        return True

    def __repr__(self):
        return "<Inter %r>" % self.__res

    def __and__(self, other):
        if isinstance(other, Inter):
            return Inter(self.__res + other.__res)
        else: return Inter(self.__res + [other])
    __rand__ = __and__

    def __or__(self, other):
        if not isinstance(other, Union):
            return Union([self, other])
        return NotImplemented

# True if the object doesn't match its RE.
class Neg(object):
    def __init__(self, re):
        self.__re = re

    def search(self, data):
        return not self.__re.search(data)

    def __repr__(self):
        return "<Neg %r>" % self.__re

    def __and__(self, other):
        if not isinstance(other, Inter):
            return Inter([self, other])
        return NotImplemented

    def __or__(self, other):
        if not isinstance(other, Union):
            return Union([self, other])
        return NotImplemented

# Numeric comparisons
class Numcmp(object):
    def __init__(self, tag, op, value):
        if isinstance(tag, unicode): self.__tag = tag.encode("utf-8")
        else: self.__tag = tag
        self.__ftag = "~#" + self.__tag
        self.__op = op
        value = value.strip().lower()

        if tag in TIME_KEYS:
            if self.__op == ">": self.__op = "<"
            elif self.__op == "<": self.__op = ">"
            elif self.__op == "<=": self.__op = ">="
            elif self.__op == ">=": self.__op = "<="

        if value in ["now"]: value = int(time.time())
        elif value in ["today"]: value = int(time.time() - 24 * 60 * 60)
        else:
            parts = value.split()
            try: value = round(float(parts[0]), 2)
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
                elif unit == "gb": value *= 1024**3
                elif unit == "mb": value *= 1024**2
                elif unit == "kb": value *= 1024

                if tag in TIME_KEYS:
                    value = int(time.time() - value)

        self.__value = value

    def search(self, data):
        num = data(self.__ftag, None)
        if num is None: return False
        num = round(num, 2)
        if   self.__op == ">":  return num >  self.__value
        elif self.__op == "<":  return num <  self.__value
        elif self.__op == "=":  return num == self.__value
        elif self.__op == ">=": return num >= self.__value
        elif self.__op == "<=": return num <= self.__value
        elif self.__op == "!=": return num != self.__value
        else: raise ValueError("Unknown operator %s" % self.__op)

    def __repr__(self):
        return "<Numcmp tag=%r, op=%r, value=%d>"%(
            self.__tag, self.__op, self.__value)

    def __and__(self, other):
        if not isinstance(other, Inter):
            return Inter([self, other])
        return NotImplemented

    def __or__(self, other):
        if not isinstance(other, Union):
            return Union([self, other])
        return NotImplemented

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
        names = [Tag.ABBRS.get(n.lower(), n.lower()) for n in names]
        self.__names = [n for n in names if not n.startswith("~")]
        self.__intern = [n for n in names if n.startswith("~")]
        self.__res = res

    def search(self, data):
        for name in self.__names:
            val = data.get(name) or data.get("~"+name, "")
            if self.__res.search(val): return True
        for name in self.__intern:
            if self.__res.search(data(name)): return True
        return False

    def __repr__(self):
        names = self.__names + self.__intern
        return ("<Tag names=%r, res=%r>" % (names, self.__res))

    def __and__(self, other):
        if not isinstance(other, Inter):
            return Inter([self, other])
        return NotImplemented

    def __or__(self, other):
        if not isinstance(other, Union):
            return Union([self, other])
        return NotImplemented
