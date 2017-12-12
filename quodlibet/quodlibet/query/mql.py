# -*- encoding: utf-8 -*-
# Copyright 2011-12, 2014-15 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet.plugins import MissingModulePluginException
from quodlibet.qltk.songlist import SongList
from quodlibet.util.tags import NUMERIC_TAGS
from quodlibet.compat import text_type

try:
    from pyparsing import Literal, CaselessLiteral, Word, delimitedList,\
        Optional, Combine, Group, nums, ParseException, Forward, oneOf, \
        quotedString, ZeroOrMore, unicodeString, Regex, upcaseTokens, \
        CaselessKeyword, StringEnd, Suppress, OneOrMore, removeQuotes, alphas
except ImportError:
    raise MissingModulePluginException("pyparsing")

import re
from quodlibet import print_d, print_w
from quodlibet.query import _match as match, Query, QueryType
from quodlibet.query._match import ParseError as QlParseError, False_, \
    NumexprTag, numexprUnit
from quodlibet.query._match import Numcmp


class Error(ValueError):
    pass


class ParseError(Error):
    pass


def proc_quoted_str(string, location, tokens):
    raw = removeQuotes(string, location, tokens)
    #return "\\b%s\\b" % re.escape(raw) if len(raw) else ""
    return "^%s$" % re.escape(raw)


def proc_str(string, location, tokens):
    return re.escape(tokens[0])


def process_keyword(string, location, tokens):
    """Spaces keywords for reformatted text"""
    return [" %s " % t for t in upcaseTokens(string, location, tokens)]


class Tag(match.Tag):
    """Customised version of match.Tag for easier calling / debugging"""
    __RE_MODS = re.MULTILINE | re.UNICODE | re.IGNORECASE

    def __init__(self, value, tags, mods=__RE_MODS):
        self.__res = re.compile(value, mods)
        super(Tag, self).__init__(tags, self.__res)

    def __repr__(self):
        names = self._names + self.__intern
        return "<MQL Tag names=%r, regex=%r>" % (names, self.__res.pattern)


class Mql(Query):
    """
    A parser to model the SQL-like language 'MQL'
    Designed for ease of use whilst retaining QL "feel".

     * Whitespace is generally unimportant
     * "standard" QL queries work with partial matching across any of
     the exposed tags
     * Unquoted (single-word) values are partial matches, whilst with quoting
     results in full matching
     * conjunctions and disjunctions e.g. genre = Jazz AND rating > 0.5
     * Basic grouping of the above, e.g.
         genre=Jazz AND (filesize > 10 MB OR rating > 0.75)
     * Missing values can be used with specified with !,
       e.g. "!albumartist" to find songs with no album artist
     * Regexes e.g. "album = /[0-9]{2,3} Greatest Hits$/"
     * limiting by various sums: "LIMIT 10" (songs) or "LIMIT 720MB"

    """

    # Now some "constants" (ones that don't trigger actions)
    EQ = Literal("=").setName("=")
    NEQ = (Literal("!=") | Literal("<>")).setName("!=")
    EQ_OP = (EQ | NEQ)("EQ_OP").setParseAction(process_keyword)
    NUM_OP = oneOf("= < > >= <= !=")("NUM_OP")
    AND_ = CaselessKeyword("AND").setParseAction(process_keyword)
    OR_ = CaselessKeyword("OR").setParseAction(process_keyword)
    BUT_NOT = CaselessKeyword("BUT NOT").setParseAction(process_keyword)
    IN_ = CaselessKeyword("IN").setParseAction(process_keyword)
    JUNCTION = Group(AND_ | OR_).setName("JUNCTION")
    LIMIT = CaselessKeyword("LIMIT").setParseAction(process_keyword)
    # Master list of reserved words
    RESERVED = (JUNCTION | NUM_OP | EQ_OP | LIMIT | IN_ | BUT_NOT)

    # Some magic constants.
    UNITS = (
        CaselessKeyword("MB").setName("Megabytes") |
        CaselessKeyword("KB").setName("Kilobytes") |
        CaselessKeyword("GB").setName("Gigabytes") |
        CaselessKeyword("Songs").setName("songs") |
        (oneOf("MIN MINS MIN", caseless=True)).setName("mins") |
        (oneOf("HOUR HOURS HR", caseless=True)).setName("hours")
    )("UNITS").setParseAction(upcaseTokens)

    # Value-like tokens
    STRING = Regex(r"[\w'&\-_\?!£\$.^]+", re.UNICODE).setName("STRING")
    VALUE = (~RESERVED
             + (quotedString.setParseAction(proc_quoted_str)("QUOTED")
                | (unicodeString | STRING)("UNQUOTED").setParseAction(proc_str)
                )("REGEX"))
    # Loose definition of numeric value (note: allows 1.2.3. 12:14)
    NUM_VAL = Word(nums, nums + '.:')("NUM_VAL") + Optional(UNITS)
    # TODO: support for regex escaping e.g. /\/home\/[^\/]+\/dir/
    REGEX = Literal("/") + Regex("[^\/]*")("REGEX") + Literal("/")
    LIST_ = (Suppress("[") + Optional(delimitedList(VALUE)) + Suppress("]"))

    # Tag-related
    TAG_NAME = Word(alphas, alphas + "_.")
    INT_TAG = Combine(Literal("~") + TAG_NAME)("INT_TAG")
    NUM_TAG = (Combine(Optional(Suppress("~#")) + oneOf(NUMERIC_TAGS))
               | Combine(Literal("~#") + TAG_NAME))("NUM_TAG")
    NO_TAG = (Literal("!") + Combine(Optional(Literal("~")) + TAG_NAME)("TAG"))

    #EXCLUDE_CLAUSE = BUT_NOT + VALUE("EXCLUSION")

    EMPTY_MATCH = match.Tag("", Query.STAR)

    class Limit(object):
        """Encapsulates the limits imposed on a collection of songs
        typically by the LIMIT clause"""

        @property
        def value(self):
            return self._value

        @property
        def units(self):
            return self._units

        def __init__(self, value, units):
            if not value or not units:
                raise ValueError("Both amount and units of LIMIT are needed")
            self._value = int(value)
            self._units = str(units).upper()

    def __init__(self, string, star=None, debug=False):

        self.string = string
        if star is None:
            # Ugh. This feels wrong, but other models don't need to know
            # STAR for validity, so the validator doesn't (currently) pass it
            print_d("Using default STAR for %s" % string)
            star = SongList.star
            #star = self.STAR

        if not isinstance(string, text_type):
            string = string.decode('utf-8')

        # MQL-specifics
        self._limit = None
        self._stack = []
        self.pp_query = Forward()
        self.star = star
        self.STANDARD_TAG = oneOf(' '.join(star), caseless=True)
        self.TAG = (self.STANDARD_TAG | Mql.INT_TAG)("TAG")
        clause = Forward()
        tag_units = Combine(self.STANDARD_TAG
                            + Suppress(Optional(CaselessLiteral('s'))))(
            "UNITS")
        limit_clause = (Mql.LIMIT + Mql.NUM_VAL
                        + Optional(Mql.UNITS | tag_units))
        limit_clause.setParseAction(self.handle_limit)
        no_tag_val = Mql.NO_TAG.setParseAction(self.handle_no_tag_val)
        tag_expr = (self.TAG
                    + Mql.EQ_OP("OPERATOR")
                    + (Mql.VALUE | Mql.REGEX))
        tag_expr.setParseAction(self.handle_equality)
        exc_expr = (self.TAG
                    + Mql.EQ
                    + (Mql.VALUE | Mql.REGEX)
                    + Mql.BUT_NOT
                    + Mql.VALUE("EXCLUSION"))
        exc_expr.setParseAction(self.handle_excluded_equality)
        num_expr = (Mql.NUM_TAG + Mql.NUM_OP + Mql.NUM_VAL)
        num_expr.setParseAction(self.handle_num_expr)
        list_expr = (self.TAG + Mql.IN_ + Mql.LIST_("LIST"))
        list_expr.setParseAction(self.handle_in)
        expr = Group(
            (Literal("(") + clause + Literal(")")) |
            no_tag_val |
            num_expr |
            tag_expr |
            exc_expr |
            list_expr |
            Mql.REGEX.setParseAction(self.handle_bare_regex) |
            OneOrMore(Mql.VALUE).setParseAction(self.handle_bare_value)
        )
        clause << (expr + ZeroOrMore((Mql.JUNCTION + clause)
                                     .setParseAction(self.handle_junction)))
        self.pp_query << (Group(Optional(clause) + Optional(limit_clause))
                          + StringEnd())
        if debug:
            self.pp_query.setDebug()
        try:
            self.parse(string)
        except ParseError as e:
            print_d("Couldn't parse MQL: %s (%s)" % (string, e))
            self.type = QueryType.INVALID
            self._match = False_()
        else:
            self.type = QueryType.VALID
            self._match = self._eval_stack()
            print_d("Match object: %r" % self._match)

    def __repr__(self):
        return "<MQL string=%r type=%r star=%r>" % (
            self.string, self.type, self.star)

    def parse(self, s):
        try:
            self._limit = None
            self._stack = []
            return self.pp_query.parseString(s)
        except ParseException as e:
            raise ParseError(e)

    def push(self, x):
        self._stack.append(x)

    def pop(self):
        if self._stack:
            return self._stack.pop()

    def _eval_stack(self):
        if not self._stack:
            print_d("Empty stack")
            return self.EMPTY_MATCH
        # print_d("Here's the stack: %s" % list(reversed(self.stack)))
        try:
            x = self._stack.pop()
        except IndexError as e:
            print_w("MQL error: %s" % e)
            raise ParseError(e)
        if x == Mql.AND_:
            return match.Inter([self._eval_stack(), self._eval_stack()])
        elif x == Mql.OR_:
            return match.Union([self._eval_stack(), self._eval_stack()])
        else:
            return x

    @property
    def limit(self):
        return self._limit

    def handle_limit(self, string, location, tokens):
        print_d("LIMIT of %s (%s)" % (tokens.NUM_VAL, tokens.UNITS))
        self._limit = Mql.Limit(str(tokens.NUM_VAL), tokens.UNITS or "SONGS")

    def handle_equality(self, string, location, tokens):
        matcher = Tag(tokens.REGEX, [tokens.TAG])
        if tokens.OPERATOR == Mql.NEQ:
            matcher = match.Neg(matcher)
        self.push(matcher)

    def handle_excluded_equality(self, string, location, tokens):

        matcher = Tag(tokens.REGEX, [tokens.TAG])
        if tokens.OPERATOR == Mql.NEQ:
            matcher = match.Neg(matcher)
        print_d("Pushing matcher: %r" % matcher)
        self.push(matcher)

    def handle_num_expr(self, string, location, tokens):
        value = numexprUnit(tokens.NUM_VAL, tokens.UNIT)
        try:
            matcher = Numcmp(NumexprTag(str(tokens.NUM_TAG)),
                             str(tokens.NUM_OP),
                             value)
        except QlParseError as e:
            raise ParseError("Couldn't handle numeric expression '%s' (%s)"
                             % (string, e))
        print_d("Built numeric expression matcher: %r" % matcher)
        self.push(matcher)

    def handle_in(self, string, location, tokens):
        if len(tokens.LIST) == 1:
            matcher = Tag(tokens.LIST[0], [tokens.TAG])
        else:
            matcher = match.Union([Tag(v, [tokens.TAG])
                                  for v in tokens.LIST])
        self.push(matcher)

    def handle_junction(self, string, location, tokens):
        self.push(tokens[0][0])

    def handle_bare_value(self, string, location, tokens):
        # Use default modifiers for now
        if len(tokens) == 1:
            matcher = Tag(tokens[0], self.star)
        else:
            tags = [Tag(v, self.star) for v in tokens]
            matcher = match.Inter(tags)
        self.push(matcher)

    def handle_bare_regex(self, string, location, tokens):
        try:
            matcher = Tag(tokens.REGEX, self.star)
        except Exception:
            raise ParseError("Invalid regex: %s" % tokens.REGEX)
        self.push(matcher)

    def handle_no_tag_val(self, string, location, tokens):
        try:
            matcher = Tag('^$', [tokens.TAG])
        except Exception as e:
            raise ParseError("Invalid tag: %s (%r)" % (tokens.TAG, e))
        self.push(matcher)
