# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#           2011 Christoph Reiter
#           2016 Ryan Dellenbaugh
#        2016-22 Nick Boultbee
#           2018 Peter Strulo
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from __future__ import annotations

import operator
import time
from enum import auto, Enum
from numbers import Real
from typing import TypeVar
from collections.abc import Iterable

from quodlibet.formats import FILESYSTEM_TAGS, TIME_TAGS
from quodlibet.formats._audio import SIZE_TAGS, DURATION_TAGS
from quodlibet.unisearch import compile
from quodlibet.util import parse_date
from senf import fsn2text, fsnative

T = TypeVar("T")


class Error(ValueError):
    pass


class ParseError(Error):
    pass


class Node:
    def search(self, data: T) -> bool:
        raise NotImplementedError

    def filter(self, sequence: Iterable[T]) -> list[T]:
        return [s for s in sequence if self.search(s)]

    def _unpack(self) -> Node:
        return self

    def __or__(self, other: Node) -> Node:
        return NotImplemented

    def __and__(self, other: Node) -> Node:
        return NotImplemented

    def __neg__(self) -> Node:
        return Neg(self._unpack())

    @property
    def valid(self) -> bool:
        return True


class Regex(Node):
    def __init__(self, pattern: str, mod_string: str):
        self.pattern = str(pattern)
        self.mod_string = str(mod_string)

        ignore_case = "c" not in self.mod_string or "i" in self.mod_string
        dot_all = "s" in self.mod_string
        asym = "d" in self.mod_string
        try:
            re = compile(self.pattern, ignore_case, dot_all, asym)
            self.search = re  # type: ignore
        except ValueError as e:
            raise ParseError(
                f"The regular expression /{self.pattern}/ is invalid."
            ) from e

    def __repr__(self):
        return f"<Regex pattern={self.pattern} mod={self.mod_string}>"


class True_(Node):
    """Always True"""

    def search(self, data):
        return True

    def filter(self, sequence):
        return list(sequence)

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

    def filter(self, sequence):
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

    def __init__(self, res: list[Node]):
        self.res = res

    def search(self, data):
        for re in self.res:
            if re.search(data):
                return True
        return False

    def __repr__(self):
        return f"<Union {self.res!r}>"

    def __or__(self, other):
        other = other._unpack()

        if isinstance(other, Union):
            return Union(self.res + list(other.res))
        elif isinstance(other, True_):
            return other.__or__(self)

        return Union(self.res + [other])

    def __and__(self, other):
        other = other._unpack()

        if isinstance(other, Inter | True_):
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
        return f"<Inter {self.res!r}>"

    def __and__(self, other):
        other = other._unpack()

        if isinstance(other, Inter):
            return Inter(self.res + other.res)

        if isinstance(other, True_):
            return other.__and__(self)

        return Inter(self.res + [other])

    def __or__(self, other):
        other = other._unpack()
        if isinstance(other, Union | True_):
            return other.__or__(self)
        return Union([self, other])


class Neg(Node):
    """True if the object doesn't match its RE."""

    def __init__(self, res):
        self.res = res

    def search(self, data):
        return not self.res.search(data)

    def __repr__(self):
        return f"<Neg {self.res!r}>"

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

    def __init__(self, expr: Numexpr, op: str, expr2: Numexpr):
        self._expr = expr
        self._op = self.operators[op]
        self._expr2 = expr2
        units = expr2.units()

        if units and not expr.valid_for_units(units):
            raise ParseError(f"Wrong units for {expr}")

    def search(self, data):
        time_ = time.time()
        use_date = self._expr.use_date() or self._expr2.use_date()
        val = self._expr.evaluate(data, time_, use_date)
        val2 = self._expr2.evaluate(data, time_, use_date)
        if val is not None and val2 is not None:
            return self._op(val, val2)
        return False

    def __repr__(self):
        return (
            f"<Numcmp expr={self._expr!r}, "
            f"op={self._op.__name__!r}, "
            f"expr2={self._expr2!r}>"
        )

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

    def evaluate(self, data: T, time: float, use_date: bool):
        """Evaluate the expression to a number.
        :param data: is the audiofile to evaluate for
        :param time: is the current time
        :param use_date: whether to evaluate as a date
                         (used to handle expressions like 2015-02-11
                          that look like dates and subtraction)
        """
        raise NotImplementedError

    def use_date(self) -> bool:
        """Returns whether to force the final comparison to compare the date
        values instead of the number values."""
        return False

    def units(self) -> Units | None:
        """Returns optional (converted) units for this number"""
        return None

    def valid_for_units(self, units: Units) -> bool:
        """Returns true if the given unit is valid for this expression"""
        return True


class NumexprTag(Numexpr):
    """Numeric tag"""

    def __init__(self, tag: str):
        self._tag = tag
        self._ftag = "~#" + self._tag
        # Strip aggregate function from tag
        self._base_ftag = (self._ftag or "").split(":")[0]

    def valid_for_units(self, units: Units) -> bool:
        return self._base_ftag in UNITS_TO_TAGS[units]

    def evaluate(self, data, time, use_date):
        if self._tag == "date":
            date = data("date")
            if not date:
                return None
            try:
                num = parse_date(date)
            except ValueError:
                return None
        else:
            num = data(self._ftag, None)
        if num is not None:
            if self._base_ftag in TIME_TAGS:
                num = time - num
            return round(num, 2)
        return None

    def __repr__(self):
        return f"<NumexprTag tag={self._tag!r}>"

    def use_date(self):
        return self._tag == "date"


class NumexprUnary(Numexpr):
    """Unary numeric operation (like -)"""

    operators = {"-": operator.neg}

    def __init__(self, op: str, expr: Numexpr):
        self.__op = self.operators[op]
        self.__expr = expr

    def evaluate(self, data, time, use_date):
        val = self.__expr.evaluate(data, time, use_date)
        if val is not None:
            return self.__op(val)
        return None

    def __repr__(self):
        return f"<NumexprUnary op={self.__op!r} expr={self.__expr!r}>"

    def use_date(self):
        return self.__expr.use_date()


class NumexprBinary(Numexpr):
    """Binary numeric operation (like + or *)"""

    operators = {
        "-": operator.sub,
        "+": operator.add,
        "*": operator.mul,
        "/": operator.floordiv,
    }

    precedence = {
        operator.sub: 1,
        operator.add: 1,
        operator.mul: 2,
        operator.floordiv: 2,
    }

    def __init__(self, op: str, expr: Numexpr, expr2: Numexpr):
        self.__op = self.operators[op]
        self.__expr = expr
        self.__expr2 = expr2
        # Rearrange expressions for operator precedence
        if (
            isinstance(expr, NumexprBinary)
            and self.precedence[expr.__op] < self.precedence[self.__op]
        ):
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
                return val * float("inf")
        return None

    def __repr__(self):
        return (
            f"<NumexprBinary "
            f"op={self.__op!r} "
            f"expr={self.__expr!r} "
            f"expr2={self.__expr2!r}>"
        )

    def use_date(self):
        return self.__expr.use_date() or self.__expr2.use_date()


class NumexprGroup(Numexpr):
    """Parenthesized group in numeric expression"""

    def __init__(self, expr: Numexpr):
        self.__expr = expr

    def evaluate(self, data, time, use_date):
        return self.__expr.evaluate(data, time, use_date)

    def __repr__(self):
        return f"<NumexprGroup expr={self.__expr!r}>"

    def use_date(self):
        return self.__expr.use_date()


class NumexprNumber(Numexpr):
    """Number in numeric expression"""

    def __init__(self, value: Real, units: Units | None = None):
        self._value = float(value)
        self._units = units

    def evaluate(self, data, time, use_date):
        return self._value

    def units(self) -> Units | None:
        return self._units

    def __repr__(self):
        return f"<NumexprNumber value={self._value:.2f}>"


class NumexprNow(Numexpr):
    """Current time, with optional offset"""

    def __init__(self, offset=0):
        self.__offset = offset

    def evaluate(self, data, time, use_date):
        return time - self.__offset

    def __repr__(self):
        return f"<NumexprNow offset={self.__offset!r}>"


class NumexprNumberOrDate(Numexpr):
    """An ambiguous value like 2015-09-25 than can be interpreted as either
    a number or a date."""

    def __init__(self, date):
        self.date = parse_date(date)
        parts = date.split("-")
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
        return f"<NumexprNumberOrDate number={self.number!r} date={self.date!r}>"


class Units(Enum):
    SECONDS = auto()
    BYTES = auto()


UNITS_TO_TAGS = {Units.SECONDS: TIME_TAGS | DURATION_TAGS, Units.BYTES: SIZE_TAGS}


def numexprUnit(value, unit):
    """Process numeric units and return NumexprNumber"""

    unit = unit.lower().strip()
    converted = Units.SECONDS
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
        value *= 1024**3
        converted = Units.BYTES
    elif unit.startswith("m"):
        value *= 1024**2
        converted = Units.BYTES
    elif unit.startswith("k"):
        value *= 1024
        converted = Units.BYTES
    elif unit.startswith("b"):
        converted = Units.SECONDS
    elif unit:
        raise ParseError(f"No such unit: {unit!r}")
    return NumexprNumber(value, converted)


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
    ABBRS = {
        "a": "artist",
        "b": "album",
        "v": "version",
        "t": "title",
        "n": "tracknumber",
        "d": "date",
    }

    def __init__(self, names: Iterable[str], res):
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
                    val = data.get("~" + name, "")

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
        return f"<Tag names={names!r}, res={self.res!r}>"

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

    @property
    def valid(self) -> bool:
        return self.__valid

    def __repr__(self):
        return (
            f"<Extension "
            f"name={self.__name!r} valid={self.__valid!r} body={self.__body!r}>"
        )

    def __and__(self, other):
        other = other._unpack()

        if isinstance(other, Inter | True_):
            return other.__and__(self)

        return Inter([self] + [other])

    def __or__(self, other):
        other = other._unpack()

        if isinstance(other, Union | True_):
            return other.__or__(self)

        return Union([self, other])
