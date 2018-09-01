# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#           2016 Ryan Dellenbaugh
#           2017 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import codecs
import re

from . import _match as match
from ._match import ParseError
from quodlibet.util import re_escape
from quodlibet.compat import text_type


# Precompiled regexes
TAG = re.compile(r'[~\w\s:]+')
UNARY_OPERATOR = re.compile(r'-')
BINARY_OPERATOR = re.compile(r'[+\-\*/]')
RELATIONAL_OPERATOR = re.compile(r'>=|<=|==|!=|>|<|=')
DIGITS = re.compile(r'\d+(\.\d+)?')
WORD = re.compile(r'[ \w]+')
REGEXP = re.compile(r'([^/\\]|\\.)*')
SINGLE_STRING = re.compile(r"([^'\\]|\\.)*")
DOUBLE_STRING = re.compile(r'([^"\\]|\\.)*')
MODIFIERS = re.compile(r'[cisld]*')
TEXT = re.compile(r'[^,)]+')
DATE = re.compile(r'\d{4}(-\d{1,2}(-\d{1,2})?)?')


class QueryParser(object):
    """Parse the input. One lookahead token, start symbol is Query."""

    def __init__(self, tokens, star=[]):
        self.tokens = tokens
        self.index = 0
        self.last_match = None
        self.star = star

    def space(self):
        """Advance to the first non-space token"""
        while not self.eof() and self.tokens[self.index] == ' ':
            self.index += 1

    def accept(self, token):
        """Return whether the next token is the same as the provided token,
        and if so advance past it."""
        self.space()
        if self.eof():
            return False
        if self.tokens[self.index] == token:
            self.index += 1
            return True
        else:
            return False

    def accept_re(self, regexp):
        """Same as accept, but with a regexp instead of a single token.
        Sets self.last_match to the match text upon success"""
        self.space()
        re_match = regexp.match(self.tokens, self.index)
        if re_match:
            self.index = re_match.end()
            re_match = re_match.group()
        self.last_match = re_match
        return re_match

    def expect(self, token):
        """Raise an error if the next token doesn't match the provided token"""
        if not self.accept(token):
            raise ParseError("'{0}' expected at index {1}, but not found"
                             .format(token, self.index))

    def expect_re(self, regexp):
        """Same as expect, but with a regexp instead of a single token"""
        if self.accept_re(regexp) is None:
            raise ParseError("RE match expected at index {0}, but not found"
                             .format(self.index))
        return self.last_match

    def eof(self):
        """Return whether last token has been consumed"""
        return self.index >= len(self.tokens)

    def match_list(self, rule):
        """Match a comma-separated list of rules"""
        m = [rule()]
        while self.accept(','):
            m.append(rule())
        return m

    def StartQuery(self):
        """Match a query that extends until the end of the input"""
        s = self.Query(outer=True)
        if not self.eof():
            raise ParseError('Query ended before end of input')
        return s

    def Query(self, outer=False):
        """Rule for a query or subquery. Determines type of query based on
        first token"""
        self.space()
        if self.eof():
            return match.True_()
        elif self.accept('!'):
            return self.Negation(self.Query)
        elif self.accept('&'):
            return self.Intersection(self.Query)
        elif self.accept('|'):
            return self.Union(self.Query)
        elif self.accept('#'):
            return self.Intersection(self.Numcmp)
        elif self.accept('@'):
            return self.Extension()
        try:
            # Equals, NotEquals and Star can begin the same,
            # so try in order, backtracking on failure (with Star last)
            index = self.index
            return self.Equals()
        except ParseError:
            self.index = index
            try:
                return self.NotEquals()
            except ParseError:
                self.index = index
            return self.Star(outer=outer)

    def Negation(self, rule):
        """Rule for '!query'. '!' token is consumed in Query"""
        return match.Neg(rule())

    def Intersection(self, rule):
        """Rule for '&(query, query)'. '&' token is consumed in Query"""
        self.expect('(')
        inter = match.Inter(self.match_list(rule))
        self.expect(')')
        return inter

    def Union(self, rule):
        """Rule for '|(query, query)'. '|' token is consumed in Query"""
        self.expect('(')
        union = match.Union(self.match_list(rule))
        self.expect(')')
        return union

    def Numcmp(self):
        """Rule for numerical comparison like 'length > 3:30'"""
        cmps = []
        expr2 = self.Numexpr(allow_date=True)
        while self.accept_re(RELATIONAL_OPERATOR):
            expr = expr2
            relop = self.last_match
            expr2 = self.Numexpr(allow_date=True)
            cmps.append(match.Numcmp(expr, relop, expr2))
        if not cmps:
            raise ParseError('No relational operator in numerical comparison')
        if len(cmps) > 1:
            return match.Inter(cmps)
        else:
            return cmps[0]

    def Numexpr(self, allow_date=False):
        """Rule for numerical expression like 'playcount + 4'"""
        if self.accept('('):
            expr = match.NumexprGroup(self.Numexpr(allow_date=True))
            self.expect(')')
        elif self.accept_re(UNARY_OPERATOR):
            expr = match.NumexprUnary(self.last_match, self.Numexpr())
        elif allow_date and self.accept_re(DATE):
            # Parse sequences of numbers that looks like dates as either dates
            # or numbers
            try:
                expr = match.NumexprNumberOrDate(self.last_match)
            except ValueError:
                # If the date can't be parsed then backtrack and try again
                # without allowing dates
                self.index -= len(self.last_match)
                expr = self.Numexpr(allow_date=False)
        elif self.accept_re(DIGITS):
            number = float(self.last_match)
            if self.accept(':'):
                # time like 4:15
                number2 = float(self.expect_re(DIGITS))
                expr = match.NumexprNumber(60 * number + number2)
            elif self.accept_re(WORD):
                # Number with units like 7 minutes
                expr = match.numexprUnit(number, self.last_match)
            else:
                expr = match.NumexprNumber(number)
        else:
            # Either tag name or special name like "today"
            expr = match.numexprTagOrSpecial(self.expect_re(TAG).strip())
        if self.accept_re(BINARY_OPERATOR):
            # Try matching a binary operator then the second argument
            binop = self.last_match
            expr2 = self.Numexpr()
            return match.NumexprBinary(binop, expr, expr2)
        else:
            return expr

    def Extension(self):
        """Rule for plugin use like @(plugin: arguments)"""
        self.expect('(')
        name = self.expect_re(WORD)
        if self.accept(':'):
            body = self.ExtBody()
        else:
            body = None
        self.expect(')')
        return match.Extension(name, body)

    def ExtBody(self):
        """Body of plugin expression. Matches balanced parentheses"""
        depth = 0
        index = self.index
        try:
            while True:
                current = self.tokens[index]
                if current == '(':
                    depth += 1
                elif current == ')':
                    if depth == 0:
                        break
                    depth -= 1
                elif current == '\\':
                    index += 1
                index += 1
        except IndexError:
            if depth != 0:
                raise ParseError('Unexpected end of string while parsing '
                                 'extension body')
        result = self.tokens[self.index:index]
        self.index = index
        return result

    def Equals(self):
        """Rule for 'tag=value' queries"""
        tags = self.match_list(lambda: self.expect_re(TAG))
        tags = [tag.strip() for tag in tags]
        self.expect('=')
        value = self.Value()
        return match.Tag(tags, value)

    def NotEquals(self):
        """Rule for 'tag!=value' queries"""
        tags = self.match_list(lambda: self.expect_re(TAG))
        tags = [tag.strip() for tag in tags]
        self.expect('!')
        self.expect('=')
        value = self.Value()
        return match.Neg(match.Tag(tags, value))

    def Value(self, outer=False):
        """Rule for value. Either a regexp, quoted string, boolean combination
        of values, or free text string"""
        if self.accept('/'):
            regex = self.expect_re(REGEXP)
            self.expect('/')
            return self.RegexpMods(regex)
        elif self.accept('"'):
            regex = self.str_to_re(self.expect_re(DOUBLE_STRING))
            self.expect('"')
            return self.RegexpMods(regex)
        elif self.accept("'"):
            regex = self.str_to_re(self.expect_re(SINGLE_STRING))
            self.expect("'")
            return self.RegexpMods(regex)
        elif self.accept('!'):
            return self.Negation(self.Value)
        elif self.accept('|'):
            return self.Union(self.Value)
        elif self.accept('&'):
            return self.Intersection(self.Value)
        else:
            if outer:
                # Hack to force plain text parsing for top level free text
                raise ParseError('Free text not allowed at top level of query')

            return match.Regex(re_escape(self.expect_re(TEXT)), u"d")

    def RegexpMods(self, regex):
        """Consume regexp modifiers from tokens and compile provided regexp
        with them.
        """

        mod_string = self.expect_re(MODIFIERS)
        return match.Regex(regex, mod_string)

    def Star(self, outer=False):
        """Rule for value that matches all visible tags"""
        return match.Tag(self.star, self.Value(outer=outer))

    def str_to_re(self, string):
        """Convert plain string to escaped regexp that can be compiled"""
        if isinstance(string, text_type):
            string = string.encode('utf-8')
        string = codecs.escape_decode(string)[0]
        string = string.decode('utf-8')
        return "^%s$" % re_escape(string)
