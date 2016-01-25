# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#           2011 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import time
import operator

from quodlibet.util.path import fsdecode
from quodlibet.util import date_key, validate_query_date, parse_date


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
        val = self.__expr.evaluate(data)
        val2 = self.__expr2.evaluate(data)
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
    
    def evaluate(self, data):
        raise NotImplementedError
    
class NumexprTag(Numexpr):
    """Numeric tag"""

    def __init__(self, tag):
        if isinstance(tag, unicode):
            self.__tag = tag.encode("utf-8")
        else:
            self.__tag = tag

        self.__ftag = "~#" + self.__tag
    
    def evaluate(self, data):
        num = data(self.__ftag, None)
        if num is not None:
            if self.__ftag in TIME_KEYS:
                num = time.time() - num
            return round(num, 2)
        return None
    
    def __repr__(self):
        return "<NumexprTag tag=%r>" % self.__tag
    
class NumexprUnary(Numexpr):
    """Unary numeric operation (like -)"""
    
    operators = {
        '-': operator.neg
    }

    def __init__(self, op, expr):
        self.__op = self.operators[op]
        self.__expr = expr
    
    def evaluate(self, data):
        val = self.__expr.evaluate(data)
        if val is not None:
            return self.__op(val)
        return None
    
    def __repr__(self):
        return "<NumexprUnary op=%r expr=%r>" % (self.__op, self.__expr)
    
class NumexprBinary(Numexpr):
    """Binary numeric operation (like + or *)"""
    
    operators = {
        '-': operator.sub,
        '+': operator.add,
        '*': operator.mul,
        '/': operator.div,
    }
    
    precedence = {
        operator.sub: 1,
        operator.add: 1,
        operator.mul: 2,
        operator.div: 2,
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
    
    def evaluate(self, data):
        val = self.__expr.evaluate(data)
        val2 = self.__expr2.evaluate(data)
        if val is not None and val2 is not None:
            return self.__op(val, val2)
        return None
    
    def __repr__(self):
        return "<NumexprBinary op=%r expr=%r expr2=%r>" % (
            self.__op, self.__expr, self.__expr2)
    
class NumexprGroup(Numexpr):
    """Parenthesized group in numeric expression"""

    def __init__(self, expr):
        self.__expr = expr
    
    def evaluate(self, data):
        return self.__expr.evaluate(data)
    
    def __repr__(self):
        return "<NumexprGroup expr=%r>" % (self.__expr)
    
class NumexprNumber(Numexpr):
    """Number in numeric expression"""
    
    def __init__(self, value):
        self.__value = float(value)
        
    def evaluate(self, data):
        return self.__value
    
    def __repr__(self):
        return "<NumexprNumber value=%.2f>" % (self.__value)
    
def numexprUnit(value, unit):
    """Process numeric units and return NumexprNumber"""
    
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
        return NumexprNumber(time.time())
    if tag == "today":
        return NumexprNumber(time.time() - 24 * 60 * 60)
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
    
# TODO add search plugin that uses Extension
class Extension(Node):
    """Plugin-defined query extension
    
    Syntax is @(plugin_name) or @(plugin_name: body)
    
    Returns false for all names until search plugins are implemented"""
    
    def __init__(self, name, body):
        self.__name = name
        self.__body = body
        
    def search(self, data):
        return False


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

    operators = {
        "<": operator.lt,
        "<=": operator.le,
        ">": operator.gt,
        ">=": operator.ge,
        "=": operator.eq,
        "!=": operator.ne,
    }

    if op not in operators:
        raise ParseError("Unknown operator %s" % op)

    inv_op = op.replace(">", "<") if op[0] == ">" else op.replace("<", ">")
    inv_op = operators[inv_op]
    op = operators[op]

    value = value.lower().strip()

    if tag == "date":
        if not validate_query_date(value):
            raise ParseError("Invalid date %r" % value)
        return (op, date_key(value))

    if tag in TIME_KEYS:
        try:
            value = parse_date(value)
        except ValueError:
            pass
        else:
            return (op, value)

        if value == "now":
            value = (time_ or time.time())
            return (inv_op, value)
        if value == "today":
            value = (time_ or time.time()) - 24 * 60 * 60
            return (inv_op, value)

    # check for time formats: "5:30"
    # TODO: handle "5:30 ago"
    try:
        hms = map(int, value.split(":"))
    except ValueError:
        pass
    else:
        if len(hms) > 1:
            value = 0
            for t in hms:
                value *= 60
                value += t
            if tag in TIME_KEYS:
                value = (time_ or time.time()) - value
                return (inv_op, value)
            return (op, value)

    # get the biggest float/int
    max_val = ""
    for i in xrange(len(value) + 1, 0, -1):
        part = value[:i]
        try:
            float(part)
        except ValueError:
            pass
        else:
            max_val = part
            break
    else:
        raise ParseError("No numeric value %r" % value)

    unit = value[len(max_val):].strip()

    try:
        value = int(max_val)
    except ValueError:
        value = float(max_val)

    if tag in TIME_KEYS:
        part = (unit.split() or [""])[0].rstrip("s")
        if part.startswith("second"):
            value = value
        elif part == "minute":
            value *= 60
        elif part == "hour":
            value *= 60 * 60
        elif part == "day":
            value *= 24 * 60 * 60
        elif part == "week":
            value *= 7 * 24 * 60 * 60
        elif part == "month":
            value *= 30 * 24 * 60 * 60
        elif part == "year":
            value *= 365 * 24 * 60 * 60
        elif unit:
            raise ParseError("No time unit: %r" % unit)
        else:
            # don't allow raw seconds since epoch. It's not that usefull
            # and overlaps with the date parsing
            # (10 would be 10 seconds, 1970 would be 0)
            raise ParseError("No valid time format")
        value = int((time_ or time.time()) - value)
        return (inv_op, value)

    if tag in SIZE_KEYS:
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
