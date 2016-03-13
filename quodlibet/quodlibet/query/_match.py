# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#           2011 Christoph Reiter, 2016 Ryan Dellenbaugh
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import time
import operator

from quodlibet.compat import floordiv
from quodlibet.util.path import fsdecode
from quodlibet.util import parse_date
from quodlibet.plugins.query import QUERY_HANDLER
from quodlibet.plugins.query import QueryPluginError


class error(ValueError):
    pass


class ParseError(error):
    pass


TIME_KEYS = ["added", "mtime", "lastplayed", "laststarted"]
SIZE_KEYS = ["filesize"]
FS_KEYS = ["~filename", "~basename", "~dirname"]


class Node(object):

    def search(self, data):
        raise NotImplementedError

    def filter(self, sequence):
        return filter(self.search, sequence)

    def _unpack(self):
        return self

    def __or__(self, other):
        return NotImplemented

    def __and__(self, other):
        return NotImplemented

    def __neg__(self):
        return Neg(self._unpack())


class True_(Node):
    """Always True"""

    def search(self, data):
        return True

    def filter(self, list_):
        return list(list_)

    def __repr__(self):
        return "<True>"

    def __or__(self, other):
        return self

    def __and__(self, other):
        other = other._unpack()
        return other


class Union(Node):
    """True if the object matches any of its REs."""

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
        other = other._unpack()

        if isinstance(other, Union):
            return Union(self.res + other.res)
        elif isinstance(other, True_):
            return other.__or__(self)

        return Union(self.res + [other])

    def __and__(self, other):
        other = other._unpack()

        if isinstance(other, (Inter, True_)):
            return other.__and__(self)

        return Inter([self, other])


class Inter(Node):
    """True if the object matches all of its REs."""

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
        other = other._unpack()

        if isinstance(other, Inter):
            return Inter(self.res + other.res)

        if isinstance(other, True_):
            return other.__and__(self)

        return Inter(self.res + [other])

    def __or__(self, other):
        other = other._unpack()
        if isinstance(other, (Union, True_)):
            return other.__or__(self)
        return Union([self, other])


class Neg(Node):
    """True if the object doesn't match its RE."""

    def __init__(self, res):
        self.res = res

    def search(self, data):
        return not self.res.search(data)

    def __repr__(self):
        return "<Neg %r>" % self.res

    def __and__(self, other):
        other = other._unpack()
        if isinstance(other, True_):
            return other.__and__(self)
        return Inter([self, other])

    def __or__(self, other):
        other = other._unpack()
        if isinstance(other, True_):
            return other.__or__(self)
        return Union([self, other])

    def __neg__(self):
        return self.res


class Numcmp(Node):
    """Numeric comparisons"""

    operators = {
        "<": operator.lt,
        "<=": operator.le,
        ">": operator.gt,
        ">=": operator.ge,
        "=": operator.eq,
        "==": operator.eq,
        "!=": operator.ne,
    }

    def __init__(self, expr, op, expr2):
        self.__expr = expr
        self.__op = self.operators[op]
        self.__expr2 = expr2

    def search(self, data):
        time_ = time.time()
        use_date = self.__expr.use_date() or self.__expr2.use_date()
        val = self.__expr.evaluate(data, time_, use_date)
        val2 = self.__expr2.evaluate(data, time_, use_date)
        if val is not None and val2 is not None:
            return self.__op(val, val2)
        return False

    def __repr__(self):
        return "<Numcmp expr=%r, op=%r, expr2=%r>" % (
            self.__expr, self.__op.__name__, self.__expr2)

    def __and__(self, other):
        other = other._unpack()
        if isinstance(other, True_):
            return other.__and__(self)
        return Inter([self, other])

    def __or__(self, other):
        other = other._unpack()
        if isinstance(other, True_):
            return other.__or__(self)
        return Union([self, other])


class Numexpr(object):
    """Expression in numeric comparison"""

    def evaluate(self, data, time, use_date):
        """Evaluate the expression to a number. `data` is the audiofile to
        evaluate for, time is the current time, and is_date is a boolean
        indicating whether to evaluate as a date (used to handle expressions
        like 2015-02-11 that look like dates and subtraction)"""
        raise NotImplementedError

    def use_date(self):
        """Returns whether to force the final comparison to compare the date
        values instead of the number values."""
        return False


class NumexprTag(Numexpr):
    """Numeric tag"""

    def __init__(self, tag):
        if isinstance(tag, unicode):
            self.__tag = tag.encode("utf-8")
        else:
            self.__tag = tag

        self.__ftag = "~#" + self.__tag

    def evaluate(self, data, time, use_date):
        if self.__tag == 'date':
            date = data('date')
            if not date:
                return None
            try:
                num = parse_date(date)
            except ValueError:
                return None
        else:
            num = data(self.__ftag, None)
        if num is not None:
            if self.__tag in TIME_KEYS:
                num = time - num
            return round(num, 2)
        return None

    def __repr__(self):
        return "<NumexprTag tag=%r>" % self.__tag

    def use_date(self):
        return self.__tag == 'date'


class NumexprUnary(Numexpr):
    """Unary numeric operation (like -)"""

    operators = {
        '-': operator.neg
    }

    def __init__(self, op, expr):
        self.__op = self.operators[op]
        self.__expr = expr

    def evaluate(self, data, time, use_date):
        val = self.__expr.evaluate(data, time, use_date)
        if val is not None:
            return self.__op(val)
        return None

    def __repr__(self):
        return "<NumexprUnary op=%r expr=%r>" % (self.__op, self.__expr)

    def use_date(self):
        return self.__expr.use_date()


class NumexprBinary(Numexpr):
    """Binary numeric operation (like + or *)"""

    operators = {
        '-': operator.sub,
        '+': operator.add,
        '*': operator.mul,
        '/': floordiv,
    }

    precedence = {
        operator.sub: 1,
        operator.add: 1,
        operator.mul: 2,
        floordiv: 2,
    }

    def __init__(self, op, expr, expr2):
        self.__op = self.operators[op]
        self.__expr = expr
        self.__expr2 = expr2
        # Rearrange expressions for operator precedence
        if (isinstance(self.__expr, NumexprBinary) and
                self.precedence[self.__expr.__op] <
                self.precedence[self.__op]):
            self.__expr = expr.__expr
            self.__op = expr.__op
            expr.__expr = expr.__expr2
            expr.__op = self.operators[op]
            expr.__expr2 = expr2
            self.__expr2 = expr

    def evaluate(self, data, time, use_date):
        val = self.__expr.evaluate(data, time, use_date)
        val2 = self.__expr2.evaluate(data, time, use_date)
        if val is not None and val2 is not None:
            return self.__op(val, val2)
        return None

    def __repr__(self):
        return "<NumexprBinary op=%r expr=%r expr2=%r>" % (
            self.__op, self.__expr, self.__expr2)

    def use_date(self):
        return self.__expr.use_date() or self.__expr2.use_date()


class NumexprGroup(Numexpr):
    """Parenthesized group in numeric expression"""

    def __init__(self, expr):
        self.__expr = expr

    def evaluate(self, data, time, use_date):
        return self.__expr.evaluate(data, time, use_date)

    def __repr__(self):
        return "<NumexprGroup expr=%r>" % (self.__expr)

    def use_date(self):
        return self.__expr.use_date()


class NumexprNumber(Numexpr):
    """Number in numeric expression"""

    def __init__(self, value):
        self.__value = float(value)

    def evaluate(self, data, time, use_date):
        return self.__value

    def __repr__(self):
        return "<NumexprNumber value=%.2f>" % (self.__value)


class NumexprNow(Numexpr):
    """Current time, with optional offset"""

    def __init__(self, offset=0):
        self.__offset = offset

    def evaluate(self, data, time, use_date):
        return time - self.__offset

    def __repr__(self):
        return "<NumexprNow offset=%r>" % (self.__offset)


class NumexprNumberOrDate(Numexpr):
    """An ambiguous value like 2015-09-25 than can be interpreted as either
    a number or a date."""

    def __init__(self, date):
        self.date = parse_date(date)
        parts = date.split('-')
        self.number = int(parts[0])
        if len(parts) > 1:
            self.number -= int(parts[1])
        if len(parts) > 2:
            self.number -= int(parts[2])

    def evaluate(self, data, time, use_date):
        if use_date:
            return self.date
        else:
            return self.number

    def __repr__(self):
        return ('<NumexprNumberOrDate number=%r date=%r>' %
            (self.number, self.date))


def numexprUnit(value, unit):
    """Process numeric units and return NumexprNumber"""

    unit = unit.lower().strip()

    # Time units
    if unit.startswith("second"):
        value = value
    elif unit.startswith("minute"):
        value *= 60
    elif unit.startswith("hour"):
        value *= 60 * 60
    elif unit.startswith("day"):
        value *= 24 * 60 * 60
    elif unit.startswith("week"):
        value *= 7 * 24 * 60 * 60
    elif unit.startswith("month"):
        value *= 30 * 24 * 60 * 60
    elif unit.startswith("year"):
        value *= 365 * 24 * 60 * 60
    # Size units
    elif unit.startswith("g"):
        value *= 1024 ** 3
    elif unit.startswith("m"):
        value *= 1024 ** 2
    elif unit.startswith("k"):
        value *= 1024
    elif unit.startswith("b"):
        pass
    elif unit:
        raise ParseError("No such unit: %r" % unit)
    return NumexprNumber(value)


def numexprTagOrSpecial(tag):
    """Handle special values that look like tags"""

    if tag == "now":
        return NumexprNow()
    if tag == "today":
        return NumexprNow(offset=24 * 60 * 60)
    else:
        return NumexprTag(tag)


class Tag(Node):
    """See if a property of the object matches its RE."""

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
                if name.startswith("~#"):
                    raise ValueError("numeric tags not supported")
                if name in FS_KEYS:
                    self.__fs.append(name)
                else:
                    self.__intern.append(name)
            else:
                self.__names.append(name)

    def search(self, data):
        for name in self.__names:
            val = data.get(name)
            if val is None:
                # filename is the only real entry that's a path
                if name == "filename":
                    val = fsdecode(data.get("~filename", ""))
                else:
                    val = data.get("~" + name, "")

            if self.res.search(unicode(val)):
                return True

        for name in self.__intern:
            if self.res.search(unicode(data(name))):
                return True

        for name in self.__fs:
            if self.res.search(fsdecode(data(name))):
                return True

        return False

    def __repr__(self):
        names = self.__names + self.__intern
        return ("<Tag names=%r, res=%r>" % (names, self.res))

    def __and__(self, other):
        other = other._unpack()
        if isinstance(other, True_):
            return other.__and__(self)
        return Inter([self, other])

    def __or__(self, other):
        other = other._unpack()
        if isinstance(other, True_):
            return other.__or__(self)
        return Union([self, other])


class Extension(Node):
    """Plugin-defined query extension

    Syntax is @(plugin_name) or @(plugin_name: body)

    Raises a ParseError if no plugin is loaded for the name, or if the plugin
    fails to parse the body"""

    def __init__(self, name, body):
        self.__name = name
        self.__valid = True
        self.__body = body

        try:
            self.__plugin = QUERY_HANDLER.get_plugin(name)
        except KeyError:
            self.__valid = False
            return

        try:
            self.__body = self.__plugin.parse_body(body)
        except QueryPluginError:
            self.__valid = False
            return

    def search(self, data):
        return self.__valid and self.__plugin.search(data, self.__body)

    def __repr__(self):
        return ('<Extension name=%r valid=%r body=%r>'
                % (self.__name, self.__valid, self.__body))
