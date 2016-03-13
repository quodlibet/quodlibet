# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#           2015-2016 Nick Boultbee,
#                2016 Ryan Dellenbaugh
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from . import _match as match
from ._match import error, Node
from ._parser import QueryParser
from quodlibet.util import re_escape, enum, cached_property


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

    def __init__(self, string, star=None, dumb_match_diacritics=True):
        """Parses the query string and returns a match object.

        star -- List of tags to look in if none are specified in the query.
                Defaults to those specified in `STAR`.

        dumb_match_diacritics -- In case of text queries (QueryType.TEXT)
                                 try to match variants with diacritic marks.

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

        # TODO dumb_match_diacritics

        if star is None:
            star = self.STAR

        if not isinstance(string, unicode):
            string = string.decode('utf-8')

        self.star = list(star)
        self.string = string

        self.type = QueryType.VALID
        try:
            self._match = QueryParser(string, star=star).StartQuery()
            return
        except error:
            pass

        if not set("#=").intersection(string):
            parts = ["/%s/" % re_escape(s) for s in string.split()]
            if dumb_match_diacritics:
                parts = [p + "d" for p in parts]
            string = "&(" + ",".join(parts) + ")"
            self.string = string

            try:
                self.type = QueryType.TEXT
                self._match = QueryParser(string, star=star).StartQuery()
                return
            except error:
                pass

        raise error('Query is not VALID or TEXT')

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

    @classmethod
    def is_valid(cls, string):
        """Whether a full query can be parsed"""

        return cls.get_type(string) == QueryType.VALID

    @classmethod
    def match_all(cls, string):
        """Whether the resulting query will not filter anything"""

        try:
            return isinstance(cls(string)._match, match.True_)
        except cls.error:
            return False

    @classmethod
    def is_parsable(cls, string):
        """Whether the text can be parsed"""

        try:
            cls(string)
        except cls.error:
            return False
        return True

    @classmethod
    def get_type(cls, string):
        """Returns a QueryType instance for the given query"""

        try:
            return cls(string).type
        except error:
            return QueryType.INVALID

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
