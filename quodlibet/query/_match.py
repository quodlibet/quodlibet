# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#           2011 Christoph Reiter
#           2016 Ryan Dellenbaugh
#        2016-17 Nick Boultbee
#           2018 Peter Strulo
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import time
import operator

from senf import fsn2text, fsnative

from quodlibet.unisearch import compile
from quodlibet.util import parse_date
from quodlibet.formats import FILESYSTEM_TAGS, TIME_TAGS


class error(ValueError):
    pass


class ParseError(error):
    pass


class Node:

    def search(self, data):
        raise NotImplementedError

    def filter(self, sequence):
        return [s for s in sequence if self.search(s)]

    def _unpack(self):
        return self

    def __or__(self, other):
        return NotImplemented

    def __and__(self, other):
        return NotImplemented

    def __neg__(self):
        return Neg(self._unpack())


class Regex(Node):

    def __init__(self, pattern, mod_string):
        self.pattern = str(pattern)
        self.mod_string = str(mod_string)

        ignore_case = "c" not in self.mod_string or "i" in self.mod_string
        dot_all = "s" in self.mod_string
        asym = "d" in self.mod_string
        try:
            self.search = compile(self.pattern, ignore_case, dot_all, asym)
        except ValueError:
            raise ParseError(
                "The regular expression /%s/ is invalid." % self.pattern)

    def __repr__(self):
        return "<Regex pattern=%s mod=%s>" % (self.pattern, self.mod_string)


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


class False_(Node):
    """Always False"""

    def search(self, data):
        return False

    def filter(self, list_):
        return []

    def __repr__(self):
        return "<False>"

    def __or__(self, other):
        other = other._unpack()
        return other

    def __and__(self, other):
        return self


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

    def filter(self, sequence):
        current = sequence
        for re in self.res:
            current = filter(re.search, current)
        if not isinstance(current, list):
            current = list(current)
        return current

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
        self._expr = expr
        self._op = self.operators[op]
        self._expr2 = expr2

    def search(self, data):
        time_ = time.time()
        use_date = self._expr.use_date() or self._expr2.use_date()
        val = self._expr.evaluate(data, time_, use_date)
        val2 = self._expr2.evaluate(data, time_, use_date)
        if val is not None and val2 is not None:
            return self._op(val, val2)
        return False

    def __repr__(self):
        return "<Numcmp expr=%r, op=%r, expr2=%r>" % (
            self._expr, self._op.__name__, self._expr2)

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


class Numexpr:
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
        self._tag = tag
        self._ftag = "~#" + self._tag

    def evaluate(self, data, time, use_date):
        if self._tag == 'date':
            date = data('date')
            if not date:
                return None
            try:
                num = parse_date(date)
            except ValueError:
                return None
        else:
            num = data(self._ftag, None)
        if num is not None:
            # Strip aggregate function from tag
            func_start = self._ftag.find(":")
            tag = self._ftag[:func_start] if func_start >= 0 else self._ftag
            if tag in TIME_TAGS:
                num = time - num
            return round(num, 2)
        return None

    def __repr__(self):
        return "<NumexprTag tag=%r>" % self._tag

    def use_date(self):
        return self._tag == 'date'


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
        '/': operator.floordiv,
    }

    precedence = {
        operator.sub: 1,
        operator.add: 1,
        operator.mul: 2,
        operator.floordiv: 2,
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
            try:
                return self.__op(val, val2)
            except ZeroDivisionError:
                return val * float('inf')
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
        self._value = float(value)

    def evaluate(self, data, time, use_date):
        return self._value

    def __repr__(self):
        return "<NumexprNumber value=%.2f>" % (self._value)


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
        self._names = []
        self.__intern = []
        self.__fs = []

        names = [Tag.ABBRS.get(n.lower(), n.lower()) for n in names]
        for name in names:
            if name[:1] == "~":
                if name.startswith("~#"):
                    raise ValueError("numeric tags not supported")
                if name in FILESYSTEM_TAGS:
                    self.__fs.append(name)
                else:
                    self.__intern.append(name)
            else:
                self._names.append(name)

    def search(self, data):
        search = self.res.search
        fs_default = fsnative()

        for name in self._names:
            val = data.get(name)
            if val is None:
                if name in ("filename", "mountpoint"):
                    val = fsn2text(data.get("~" + name, fs_default))
                else:
                    val = data.get("~" + name, u"")

            if search(val):
                return True

        for name in self.__intern:
            if search(data(name)):
                return True

        for name in self.__fs:
            if search(fsn2text(data(name, fs_default))):
                return True

        return False

    def __repr__(self):
        names = self._names + self.__intern
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
        # pulls in gtk+
        from quodlibet.plugins.query import QUERY_HANDLER, QueryPluginError

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

    def __and__(self, other):
        other = other._unpack()

        if isinstance(other, (Inter, True_)):
            return other.__and__(self)

        return Inter([self] + [other])

    def __or__(self, other):
        other = other._unpack()

        if isinstance(other, (Union, True_)):
            return other.__or__(self)

        return Union([self, other])
