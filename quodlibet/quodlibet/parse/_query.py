# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

# A simple top-down parser for the query grammar. It's basically textbook,
# but it could use some cleaning up. It builds the requisite match.*
# objects as it goes, which is where the interesting stuff will happen.

import re

from quodlibet.parse import _match as match
from quodlibet.parse._scanner import Scanner
from quodlibet.parse._match import error, ParseError

# Token types.
(NEGATION, INTERSECT, UNION, OPENP, CLOSEP, EQUALS, OPENRE,
 CLOSERE, REMODS, COMMA, TAG, RE, RELOP, NUMCMP, EOF) = range(15)


class LexerError(error):
    pass


class QueryLexer(Scanner):
    def __init__(self, s):
        self.string = s.strip()
        Scanner.__init__(self,
                         [(r"/([^/\\]|\\.)*/", self.regexp),
                          (r'"([^"\\]|\\.)*"', self.str_to_re),
                          (r"'([^'\\]|\\.)*'", self.str_to_re),
                          (r"([<>]=?)|(!=)", self.relop),
                          (r"[=|()&!,#]", self.table),
                          (r"\s+", None),
                          (r"[^=)|&#/<>!,]+", self.tag)
                          ])

    def regexp(self, scanner, string):
        return QueryLexeme(RE, string[1:-1])

    def str_to_re(self, scanner, string):
        if isinstance(string, unicode):
            string = string.encode('utf-8')
        string = string[1:-1].decode('string_escape')
        string = string.decode('utf-8')
        return QueryLexeme(RE, "^%s$" % re.escape(string))

    def tag(self, scanner, string):
        return QueryLexeme(TAG, string.strip())

    def relop(self, scanner, string):
        return QueryLexeme(RELOP, string)

    def table(self, scanner, string):
        return QueryLexeme({'!': NEGATION, '&': INTERSECT, '|': UNION,
                            '(': OPENP, ')': CLOSEP, '=': EQUALS,
                            ',': COMMA, '#': NUMCMP}[string], string)

    def __iter__(self):
        s = self.scan(self.string)
        if s[1] != "":
            raise LexerError("characters left over in string")
        else:
            return iter(s[0] + [QueryLexeme(EOF, "")])


class QueryLexeme(object):
    _reverse = {NEGATION: "NEGATION", INTERSECT: "INTERSECT",
                OPENRE: "OPENRE", CLOSERE: "CLOSERE", REMODS: "REMODS",
                OPENP: "OPENP", CLOSEP: "CLOSEP", UNION: "UNION",
                EQUALS: "EQUALS", COMMA: "COMMA", TAG: "TAG", RE: "RE",
                RELOP: "RELOP", NUMCMP: "NUMCP", EOF: "EOF",
                }

    def __init__(self, typ, lexeme):
        self.type = typ
        self.lexeme = lexeme

    def __repr__(self):
        return (super(QueryLexeme, self).__repr__().split()[0] +
                " type=" + repr(self.type) + " (" +
                str(self._reverse[self.type]) +
                "), lexeme=" + repr(self.lexeme) + ">")


class QueryParser(object):
    """Parse the input. One lookahead token, start symbol is Query."""

    def __init__(self, tokens):
        self.tokens = iter(tokens)
        self.lookahead = self.tokens.next()

    def _match_parened(self, expect, ReturnType, InternalType):
        self.match(expect)
        self.match(OPENP)
        m = InternalType()
        if len(m) > 1:
            m = ReturnType(m)
        else:
            m = m[0]
        self.match(CLOSEP)
        return m

    def _match_list(self, InternalType):
        l = [InternalType()]
        while self.lookahead.type == COMMA:
            self.match(COMMA)
            l.append(InternalType())
        return l

    def Query(self):
        if self.lookahead.type == UNION:
            return self.QueryUnion()
        elif self.lookahead.type == INTERSECT:
            return self.QueryInter()
        elif self.lookahead.type == NEGATION:
            return self.QueryNeg()
        elif self.lookahead.type == NUMCMP:
            return self.QueryNumcmp()
        elif self.lookahead.type == TAG:
            return self.QueryPart()
        else:
            raise ParseError("The expected symbol should be |, &, !, #, or "
                             "a tag name, but was %s" % self.lookahead.lexeme)

    def StartQuery(self):
        s = self.Query()
        self.match(EOF)
        return s

    def StartStarQuery(self, star):
        s = self.RegexpSet(no_tag=True)
        self.match(EOF)

        def insert_tags(p):
            # pack all values in tags
            if isinstance(p, match.Inter):
                return match.Inter([match.Tag(star, v) for v in p.res])
            elif isinstance(p, match.Union):
                return match.Union([match.Tag(star, v) for v in p.res])
            elif isinstance(p, match.Neg):
                # we want Neg to negate the whole query, not the value
                return match.Neg(insert_tags(p.res))
            else:
                return match.Tag(star, p)

        return insert_tags(s)

    def QueryNeg(self):
        self.match(NEGATION)
        return match.Neg(self.Query())

    def QueryInter(self):
        return self._match_parened(INTERSECT, match.Inter, self.QueryList)

    def QueryUnion(self):
        return self._match_parened(UNION, match.Union, self.QueryList)

    def QueryNumcmp(self):
        return self._match_parened(NUMCMP, match.Inter, self.NumcmpList)

    def QueryList(self):
        return self._match_list(self.Query)

    def NumcmpList(self):
        return self._match_list(self.Numcmp)

    def Numcmp(self):
        tag = self.lookahead.lexeme
        self.match(TAG)
        op = self.lookahead.lexeme
        self.match(RELOP, EQUALS)
        value = self.lookahead.lexeme
        self.match(TAG)
        if self.lookahead.type in [RELOP, EQUALS]:
            # Reverse the first operator
            tag, value = value, tag
            op = {">": "<", "<": ">", "<=": ">=", "<=": ">="}.get(op, op)
            op2 = self.lookahead.lexeme
            self.match(RELOP, EQUALS)
            val2 = self.lookahead.lexeme
            self.match(TAG)
            return match.Inter([match.Numcmp(tag, op, value),
                                match.Numcmp(tag, op2, val2)])
        else:
            return match.Numcmp(tag, op, value)

    def _match_string(self):
        s = self.lookahead.lexeme
        self.match(self.lookahead.type)
        return s

    def QueryPart(self):
        names = [s.lower() for s in self._match_list(self._match_string)]
        if filter(lambda k: k.encode("ascii", "replace") != k, names):
            raise ParseError("Expected ascii key")
        self.match(EQUALS)
        res = self.RegexpSet()
        return match.Tag(names, res)

    def RegexpSet(self, no_tag=False):
        if self.lookahead.type == UNION:
            return self.RegexpUnion()
        elif self.lookahead.type == INTERSECT:
            return self.RegexpInter()
        elif self.lookahead.type == NEGATION:
            return self.RegexpNeg()
        elif self.lookahead.type == TAG and not no_tag:
            return self.MatchTag()
        elif self.lookahead.type == RE:
            return self.Regexp()
        else:
            raise ParseError("The expected symbol should be |, &, !, or "
                             "a tag name, but was %s" % self.lookahead.lexeme)

    def RegexpNeg(self):
        self.match(NEGATION)
        return match.Neg(self.RegexpSet())

    def RegexpUnion(self):
        return self._match_parened(UNION, match.Union, self.RegexpList)

    def RegexpInter(self):
        return self._match_parened(INTERSECT, match.Inter, self.RegexpList)

    def RegexpList(self):
        return self._match_list(self.RegexpSet)

    def MatchTag(self):
        tag = self.lookahead.lexeme
        self.match(TAG)
        try:
            return re.compile(re.escape(tag), re.IGNORECASE | re.UNICODE)
        except re.error:
            raise ParseError("The regular expression was invalid")

    def Regexp(self):
        regex = self.lookahead.lexeme
        self.match(RE)
        mods = re.MULTILINE | re.UNICODE | re.IGNORECASE
        if self.lookahead.type == TAG:
            s = self.lookahead.lexeme.lower()
            if set(s) - set("cisl"):
                raise ParseError("Invalid regular expression flags: %r" % s)
            if "c" in s:
                mods &= ~re.IGNORECASE
            if "i" in s:
                mods |= re.IGNORECASE
            if "s" in s:
                mods |= re.DOTALL
            if "l" in s:
                mods = (mods & ~re.UNICODE) | re.LOCALE
            self.match(TAG)
        try:
            return re.compile(regex, mods)
        except re.error:
            raise ParseError("The regular expression /%s/ is invalid." % regex)

    def match(self, *tokens):
        if tokens == [EOF] and self.lookahead.type == EOF:
            raise ParseError("The search string ended, but more "
                             "tokens were expected.")
        try:
            if self.lookahead.type in tokens:
                self.lookahead = self.tokens.next()
            else:
                raise ParseError("The token '%s' is not the type exected." % (
                    self.lookahead.lexeme))
        except StopIteration:
            self.lookahead = QueryLexeme(EOF, "")


NORMAL, VALUE, STRING = range(3)


def _get_query_type(string):
    try:
        QueryParser(QueryLexer(string)).StartStarQuery([])
    except error:
        if not set("#=").intersection(string):
            return STRING
    else:
        return VALUE
    return NORMAL


STAR = ["artist", "album", "title"]


def Query(string, star=STAR):
    """Parses the query string and returns a match object.

    star -- List of tags to look in if none are specified in the query.
            You can add some by extending Query.START and pass it here.

    This parses the above query language as well as some tagless shortcuts:
        "foo bar" ->  &(star1,star2=foo,star1,star2=bar)
        "!foo" -> !star1,star2=foo
        "&(foo, bar)" -> &(star1,star2=foo, star1,star2=bar)
        "|(foo, bar)" -> |(star1,star2=foo, star1,star2=bar)
        "!&(foo, bar)" -> !&(star1,star2=foo, star1,star2=bar)
        "!(foo, bar)" -> !star1,star2=(foo, bar)
        etc...

    """

    if not isinstance(string, unicode):
        string = string.decode('utf-8')

    # fast path
    if Query.match_all(string):
        return match.Inter([])

    query_type = _get_query_type(string)

    # normal string, put it in a intersection to get a value list
    if query_type == STRING:
        parts = ["/%s/" % re.escape(s) for s in string.split()]
        string = "&(" + ",".join(parts) + ")"
        query_type = VALUE

    # try to parse with a taglist
    if query_type == VALUE:
        try:
            return QueryParser(QueryLexer(string)).StartStarQuery(star)
        except error:
            pass

    return QueryParser(QueryLexer(string)).StartQuery()


# default tags to search in, use/extend and pass to Query()
Query.STAR = STAR
# query base exception
Query.error = error


def is_valid(string):
    """Whether a full query can be parsed"""

    if Query.match_all(string):
        return True

    try:
        QueryParser(QueryLexer(string)).StartQuery()
    except error:
        return False
    return True
Query.is_valid = is_valid


def match_all(string):
    """Whether the resulting query will not filter anything"""

    return string.strip() == ""
Query.match_all = match_all


def is_parsable(string):
    """Whether the text can be parsed"""

    try:
        Query(string)
    except error:
        return False
    return True
Query.is_parsable = is_parsable


def is_valid_color(string):
    """Returns True/False for a query, None for a text only query"""

    if is_parsable(string):
        if _get_query_type(string) == STRING:
            return None
        else:
            return True
    return False
Query.is_valid_color = is_valid_color
