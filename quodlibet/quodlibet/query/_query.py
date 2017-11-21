# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#           2015-2017 Nick Boultbee,
#                2016 Ryan Dellenbaugh
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import print_d
from quodlibet.util.dprint import frame_info
from . import _match as match
from ._match import error, Node, False_
from ._parser import QueryParser
from quodlibet.util import re_escape, enum, cached_property
from quodlibet.compat import PY2, text_type


@enum
class QueryType(int):
    TEXT = 0
    VALID = 1
    INVALID = 2


class Query(Node):

    STAR = ["artist", "album", "title"]
    """Default tags to search in, use/extend and pass to Query()"""

    error = error
    """Base error type"""

    type = None
    """The QueryType value: VALID or TEXT"""

    string = None
    """The original string which was used to create this query"""

    stars = None
    """List of default tags used"""

    def __init__(self, string, star=None):
        """Parses the query string and returns a match object.

        star -- List of tags to look in if none are specified in the query.
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
        print_d("Creating query \"%s\", called from %s"
                % (string, frame_info(1)))
        if star is None:
            star = self.STAR

        if not isinstance(string, text_type):
            assert PY2
            string = string.decode('utf-8')

        self.star = list(star)
        self.string = string

        self.type = QueryType.VALID
        try:
            self._match = QueryParser(string, star=star).StartQuery()
            return
        except self.error:
            pass

        if not set("#=").intersection(string):
            parts = ["/%s/d" % re_escape(s) for s in string.split()]
            string = "&(" + ",".join(parts) + ")"
            self.string = string

            try:
                self.type = QueryType.TEXT
                self._match = QueryParser(string, star=star).StartQuery()
                return
            except self.error:
                pass

        # raise error('Query is not VALID or TEXT')
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
        except error:
            return None

    def __repr__(self):
        return "<Query string=%r type=%r star=%r>" % (
            self.string, self.type, self.star)

    @cached_property
    def search(self):
        return self._match.search

    @cached_property
    def filter(self):
        return self._match.filter

    @property
    def valid(self):
        """Whether a query is a valid full (not free-text) query"""
        return self.type == QueryType.VALID

    @property
    def matches_all(self):
        """Whether the resulting query will not filter anything"""
        return isinstance(self._match, match.True_)

    @property
    def is_parsable(self):
        """Whether the text can be parsed at all"""
        return self.type is not QueryType.INVALID

    def _unpack(self):
        # so that other classes can see the wrapped one and optimize
        # the result using the type information
        return self._match

    def __or__(self, other):
        return self._match.__or__(other)

    def __and__(self, other):
        return self._match.__and__(other)

    def __neg__(self):
        return self._match.__neg__()

    @classmethod
    def validator(cls, string):
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
