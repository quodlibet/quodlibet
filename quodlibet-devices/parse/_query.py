# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

# A simple top-down parser for the query grammar. It's basically textbook,
# but it could use some cleaning up. It builds the requisite match.*
# objects as it goes, which is where the interesting stuff will happen.

import re

import parse._match as match

# Token types.
(NEGATION, INTERSECT, UNION, OPENP, CLOSEP, EQUALS, OPENRE,
 CLOSERE, REMODS, COMMA, TAG, RE, RELOP, NUMCMP, EOF) = range(15)

class error(ValueError): pass
class ParseError(error): pass
class LexerError(error): pass

class QueryLexer(re.Scanner):
    def __init__(self, s):
        self.string = s.strip()
        re.Scanner.__init__(self,
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
        if isinstance(string, unicode): string = string.encode('utf-8')
        string = string[1:-1].decode('string_escape')
        string = string.decode('utf-8')
        return QueryLexeme(RE, "^%s$" % re.escape(string))

    def tag(self, scanner, string):
        return QueryLexeme(TAG, string.strip())

    def relop(self, scanner, string):
        return QueryLexeme(RELOP, string)

    def table(self, scanner, string):
        return QueryLexeme({ '!': NEGATION, '&': INTERSECT, '|': UNION,
                             '(': OPENP, ')': CLOSEP, '=': EQUALS,
                             ',': COMMA, '#': NUMCMP }[string], string)

    def __iter__(self):
        s = self.scan(self.string)
        if s[1] != "": raise LexerError("characters left over in string")
        else: return iter(s[0] + [QueryLexeme(EOF, "")])

class QueryLexeme(object):
    _reverse = { NEGATION: "NEGATION", INTERSECT: "INTERSECT",
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
    
# Parse the input. One lookahead token, start symbol is Query.
class QueryParser(object):
    def __init__(self, tokens):
        self.tokens = iter(tokens)
        self.lookahead = self.tokens.next()

    def _match_parened(self, expect, ReturnType, InternalType):
        self.match(expect)
        self.match(OPENP)
        m = ReturnType(InternalType())
        self.match(CLOSEP)
        return m

    def _match_list(self, InternalType):
        l = [InternalType()]
        while self.lookahead.type == COMMA:
            self.match(COMMA)
            l.append(InternalType())
        return l

    def Query(self):
        if self.lookahead.type == UNION: return self.QueryUnion()
        elif self.lookahead.type == INTERSECT: return self.QueryInter()
        elif self.lookahead.type == NEGATION: return self.QueryNeg()
        elif self.lookahead.type == NUMCMP: return self.QueryNumcmp()
        elif self.lookahead.type == TAG: return self.QueryPart()
        else:
            raise ParseError("The expected symbol should be |, &, !, #, or "
                             "a tag name, but was %s" % self.lookahead.lexeme)

    def StartQuery(self):
        s = self.Query()
        self.match(EOF)
        return s

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
        self.match(EQUALS)
        res = self.RegexpSet()
        return match.Tag(names, res)

    def RegexpSet(self):
        if self.lookahead.type == UNION: return self.RegexpUnion()
        elif self.lookahead.type == INTERSECT: return self.RegexpInter()
        elif self.lookahead.type == NEGATION: return self.RegexpNeg()
        elif self.lookahead.type == TAG: return self.MatchTag()
        elif self.lookahead.type == RE: return self.Regexp()
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
        try: return re.compile(re.escape(tag), re.IGNORECASE | re.UNICODE)
        except re.error:
            raise ParseError("The regular expression was invalid")

    def Regexp(self):
        regex = self.lookahead.lexeme
        self.match(RE)
        mods = re.MULTILINE | re.UNICODE | re.IGNORECASE
        if self.lookahead.type == TAG:
            s = self.lookahead.lexeme.lower()
            if "c" in s: mods &= ~re.IGNORECASE
            if "i" in s: mods |= re.IGNORECASE
            if "s" in s: mods |= re.DOTALL
            if "l" in s: mods = (mods & ~re.UNICODE) | re.LOCALE
            self.match(TAG)
        try: return re.compile(regex, mods)
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
                raise ParseError("The token '%s' is not the type exected." %(
                    self.lookahead.lexeme))
        except StopIteration:
            self.lookahead = QueryLexeme(EOF, "")

STAR = ["artist", "album", "title"]
def Query(string, star=STAR):
    if not isinstance(string, unicode): string = string.decode('utf-8')
    if string == "": return match.Inter([])
    elif not set("#=").intersection(string):
        parts = ["%s = /%s/" % (", ".join(star), re.escape(p))
                 for p in string.split()]
        string = "&(" + ",".join(parts) + ")"
    return QueryParser(QueryLexer(string)).StartQuery()
Query.STAR = STAR

def is_valid(string):
    if string == "": return True
    tokens = QueryLexer(string)
    try: QueryParser(tokens).StartQuery()
    except error: return False
    else: return True
Query.is_valid = is_valid

def is_parsable(string):
    if not set("#=").intersection(string): return True
    else: return is_valid(string)
Query.is_parsable = is_parsable

def is_valid_color(string):
    if is_valid(string): return "dark green"
    elif not (string and set("#=").intersection(string)):
        return "blue"
    else: return "red"
Query.is_valid_color = is_valid_color

Query.error = error
