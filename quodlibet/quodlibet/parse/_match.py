# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#           2011 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import time
import operator

from quodlibet.util import fsdecode


class error(ValueError):
    pass


class ParseError(error):
    pass


TIME_KEYS = ["added", "mtime", "lastplayed", "laststarted"]
SIZE_KEYS = ["filesize"]
FS_KEYS = ["~filename", "~basename", "~dirname"]


# True if the object matches any of its REs.
class Union(object):
    def __init__(self, res):
        self.res = res

    def search(self, data):
        for re in self.res:
            if re.search(data):
                return True
        return False

    def __repr__(self):
        return "<Union %r>" % self.res

    def __or__(self, other):
        if isinstance(other, Union):
            return Union(self.res + other.res)
        else:
            return Union(self.res + [other])
    __ror__ = __or__

    def __and__(self, other):
        if not isinstance(other, Inter):
            return Inter([self, other])
        return NotImplemented

    def __neg__(self):
        return Neg(self)


# True if the object matches all of its REs.
class Inter(object):
    def __init__(self, res):
        self.res = res

    def search(self, data):
        for re in self.res:
            if not re.search(data):
                return False
        return True

    def __repr__(self):
        return "<Inter %r>" % self.res

    def __and__(self, other):
        if isinstance(other, Inter):
            return Inter(self.res + other.res)
        else:
            return Inter(self.res + [other])
    __rand__ = __and__

    def __or__(self, other):
        if not isinstance(other, Union):
            return Union([self, other])
        return NotImplemented

    def __neg__(self):
        return Neg(self)


# True if the object doesn't match its RE.
class Neg(object):
    def __init__(self, res):
        self.res = res

    def search(self, data):
        return not self.res.search(data)

    def __repr__(self):
        return "<Neg %r>" % self.res

    def __and__(self, other):
        if not isinstance(other, Inter):
            return Inter([self, other])
        return NotImplemented

    def __or__(self, other):
        if not isinstance(other, Union):
            return Union([self, other])
        return NotImplemented

    def __neg__(self):
        return self.res


# Numeric comparisons
class Numcmp(object):
    def __init__(self, tag, op, value):
        if isinstance(tag, unicode):
            self.__tag = tag.encode("utf-8")
        else:
            self.__tag = tag

        self.__ftag = "~#" + self.__tag
        self.__op, self.__value = map_numeric_op(self.__tag, op, value)

    def search(self, data):
        num = data(self.__ftag, None)
        if num is not None:
            return self.__op(round(num, 2), self.__value)
        return False

    def __repr__(self):
        return "<Numcmp tag=%r, op=%r, value=%.2f>" % (
            self.__tag, self.__op.__name__, self.__value)

    def __and__(self, other):
        if not isinstance(other, Inter):
            return Inter([self, other])
        return NotImplemented

    def __or__(self, other):
        if not isinstance(other, Union):
            return Union([self, other])
        return NotImplemented

    def __neg__(self):
        return Neg(self)


# See if a property of the object matches its RE.
class Tag(object):

    # Shorthand for common tags.
    ABBRS = {"a": "artist",
             "b": "album",
             "v": "version",
             "t": "title",
             "n": "tracknumber",
             "d": "date",
             }

    def __init__(self, names, res):
        self.res = res
        self.__names = []
        self.__intern = []
        self.__fs = []

        names = [Tag.ABBRS.get(n.lower(), n.lower()) for n in names]
        for name in names:
            if name[:1] == "~":
                if name in FS_KEYS:
                    self.__fs.append(name)
                else:
                    self.__intern.append(name)
            else:
                self.__names.append(name)

    def search(self, data):
        for name in self.__names:
            val = data.get(name) or data.get("~" + name, "")
            if self.res.search(val):
                return True
        for name in self.__intern:
            if self.res.search(data(name)):
                return True
        for name in self.__fs:
            if self.res.search(fsdecode(data(name))):
                return True
        return False

    def __repr__(self):
        names = self.__names + self.__intern
        return ("<Tag names=%r, res=%r>" % (names, self.res))

    def __and__(self, other):
        if not isinstance(other, Inter):
            return Inter([self, other])
        return NotImplemented

    def __or__(self, other):
        if not isinstance(other, Union):
            return Union([self, other])
        return NotImplemented

    def __neg__(self):
        return Neg(self)


def map_numeric_op(tag, op, value, time_=None):
    """Maps a human readable numeric comparison to something we can use.

    Handles cases like '< 3 days', '>5MB' etc..
    If parsing fails, raises a ParseError.

    Takes a tag, an operator string and and a value string:
        op, v = map_numeric_op("added", "<", "today")

    Returns an (operator function, numeric value) tuple:
        if op(v, song("~#added")): ...

    (time_ is only used for testing)

    """

    if tag in TIME_KEYS:
        if op == ">":
            op = "<"
        elif op == "<":
            op = ">"
        elif op == "<=":
            op = ">="
        elif op == ">=":
            op = "<="

    op_fun = {"<": operator.lt, "<=": operator.le,
              ">": operator.gt, ">=": operator.ge,
              "=": operator.eq, "!=": operator.ne}.get(op, None)

    if op_fun is None:
        raise ParseError("Unknown operator %s" % op)
    op = op_fun

    value = value.lower().strip()

    if tag in TIME_KEYS:
        if value == "now":
            value = (time_ or time.time())
            return (op, value)
        if value == "today":
            value = (time_ or time.time()) - 24 * 60 * 60
            return (op, value)

    # check for time formats: "5:30"
    # TODO: handle "5:30 ago"
    try:
        hms = map(int, value.split(":"))
    except ValueError:
        pass
    else:
        value = 0
        for t in hms:
            value *= 60
            value += t
        if tag in TIME_KEYS:
            value = (time_ or time.time()) - value
        return (op, value)

    # get the biggest float/int
    max_val = ""
    for i in xrange(1, len(value) + 1):
        try:
            float(value[:i])
            max_val = value[:i]
        except ValueError:
            break

    if not max_val:
        raise ParseError("No numeric value %r" % value)

    unit = value[len(max_val):].strip()

    try:
        value = int(max_val)
    except ValueError:
        value = float(max_val)

    if tag in TIME_KEYS:
        part = unit.split()[0].rstrip("s")
        if part == "minute":
            value *= 60
        elif part == "hour":
            value *= 60 * 60
        elif part == "day":
            value *= 24 * 60 * 60
        elif part == "week":
            value *= 7 * 24 * 60 * 60
        elif part == "year":
            value *= 365 * 24 * 60 * 60
        elif unit:
            raise ParseError("No time unit: %r" % unit)
        value = int((time_ or time.time()) - value)
    elif tag in SIZE_KEYS:
        if unit.startswith("g"):
            value *= 1024 ** 3
        elif unit.startswith("m"):
            value *= 1024 ** 2
        elif unit.startswith("k"):
            value *= 1024
        elif unit.startswith("b"):
            pass
        elif unit:
            raise ParseError("No size unit: %r" % unit)
    elif unit:
        raise ParseError("Tag %r does not support units (%r)" % (tag, unit))

    return (op, value)
