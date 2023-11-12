# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#           2015-2020 Nick Boultbee,
#                2016 Ryan Dellenbaugh,
#                2019 Peter Strulo
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from __future__ import annotations

from enum import Enum, auto
from typing import TypeVar
from collections.abc import Iterable

from quodlibet import print_d, config
from quodlibet.util import re_escape, cached_property
from . import _match as match
from ._match import Error, Node, False_
from ._parser import QueryParser

T = TypeVar("T")


class QueryType(Enum):
    TEXT = auto()
    VALID = auto()
    INVALID = auto()

    def __repr__(self):
        # Compact representation
        return self._name_

    def __str__(self):
        return self._name_


class Query(Node):
    STAR: Iterable[str] = ["artist", "album", "title"]
    """Default tags to search in, use/extend and pass to Query()"""

    Error: type[Exception] = Error
    """Base error type"""

    type: QueryType | None = None
    """The QueryType value: VALID or TEXT"""

    string: str | None = None
    """The original string which was used to create this query"""

    def __init__(self, string: str, star: Iterable[str] | None = None):
        """Parses the query string and returns a match object.

        :param string: The text to parse
        :param star: Tags to look in, if none are specified in the query.
                     Defaults to those specified in `STAR`.

        This parses the query language as well as some tagless shortcuts:
            "foo bar" ->  &(star1,star2=foo,star1,star2=bar)
            "!foo" -> !star1,star2=foo
            "&(foo, bar)" -> &(star1,star2=foo, star1,star2=bar)
            "&(foo, !bar)" -> &(star1,star2=foo, !star1,star2=bar)
            "|(foo, bar)" -> |(star1,star2=foo, star1,star2=bar)
            "!&(foo, bar)" -> !&(star1,star2=foo, star1,star2=bar)
            "!(foo, bar)" -> !star1,star2=(foo, bar)
            etc...
        """
        print_d(f"Creating query {string!r}")
        if star is None:
            star = self.STAR

        assert isinstance(string, str)

        self.star = list(star)
        self.string = string

        self.type = QueryType.VALID
        try:
            self._match = QueryParser(string, star=star).StartQuery()
            if not self._match.valid:
                self.type = QueryType.INVALID
            return
        except self.Error:
            pass

        if not set("#=").intersection(string):
            for c in config.get("browsers", "ignored_characters"):
                string = string.replace(c, "")
            parts = ["/%s/d" % re_escape(s) for s in string.split()]
            string = "&(" + ",".join(parts) + ")"
            self.string = string

            try:
                self.type = QueryType.TEXT
                self._match = QueryParser(string, star=star).StartQuery()
                return
            except self.Error:
                pass

        print_d("Query '%s' is invalid" % string)
        self.type = QueryType.INVALID
        self._match = False_()

    @classmethod
    def StrictQueryMatcher(cls, string):
        """Returns a Matcher for a strict, valid (non-freetext) Query,
           or `None` if this fails.
        """
        try:
            return QueryParser(string).StartQuery()
        except Error:
            return None

    def __repr__(self) -> str:
        return f"<Query string={self.string!r} type={self.type!r} star={self.star!r}>"

    @cached_property
    def search(self):
        return self._match.search

    @cached_property
    def filter(self):
        return self._match.filter

    @property
    def valid(self) -> bool:
        """Whether a query is a valid full (not free-text) query"""
        return self.type == QueryType.VALID

    @property
    def matches_all(self) -> bool:
        """Whether the resulting query will not filter anything"""
        return isinstance(self._match, match.True_)

    @property
    def is_parsable(self) -> bool:
        """Whether the text can be parsed at all"""
        return self.type is not QueryType.INVALID

    def _unpack(self) -> Node:
        # so that other classes can see the wrapped one and optimize
        # the result using the type information
        return self._match

    def __or__(self, other: Node) -> Node:
        return self._match.__or__(other)

    def __and__(self, other: Node) -> Node:
        return self._match.__and__(other)

    def __neg__(self) -> Node:
        return self._match.__neg__()

    def __eq__(self, other) -> bool:
        return (self.string == other.string and self.star == other.star and
                self.type == other.type)

    @classmethod
    def validator(cls, string: str) -> bool | None:
        """Returns True/False for a query, None for a text only query"""

        query = cls(string)
        type_ = query.type
        if type_ == QueryType.VALID:
            # in case of an empty but valid query we say it's "text"
            if query.matches_all:
                return None
            return True
        elif type_ == QueryType.INVALID:
            return False
        return None
