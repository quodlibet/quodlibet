# Copyright 2004 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

# A simple top-down parser for the query grammar. It's basically textbook,
# but it could use some cleaning up. It builds the requisite match.*
# objects as it goes, which is where the interesting stuff will happen.

import string
import match
import sre

# Token types.
(NEGATION, INTERSECT, UNION, OPENP, CLOSEP, EQUALS, OPENRE,
 CLOSERE, REMODS, COMMA, TAG, RE, RELOP, NUMCMP, EOF) = range(15)

class error(RuntimeError): pass
class ParseError(error): pass
class LexerError(error): pass

# Iterator for tokenized input.
class QueryLexer(object):
    _reverse = { NEGATION: "NEGATION", INTERSECT: "INTERSECT",
                 OPENRE: "OPENRE", CLOSERE: "CLOSERE", REMODS: "REMODS",
                 OPENP: "OPENP", CLOSEP: "CLOSEP", UNION: "UNION",
                 EQUALS: "EQUALS", COMMA: "COMMA", TAG: "TAG", RE: "RE",
                 RELOP: "RELOP", NUMCMP: "NUMCP", EOF: "EOF",
                 }

    table = { '!': NEGATION, '&': INTERSECT, '|': UNION, '(': OPENP,
              ')': CLOSEP, '=': EQUALS, ',': COMMA,
              '/': CLOSERE, '#': NUMCMP, '>': RELOP, '<': RELOP }

    def __init__(self, string):
        self.string = string.strip()
        self.regexp_mod = False
        self.regexp_start = None
        self.regexp_end = False
        self.i = 0

    def __iter__(self): return self

    def next(self):
        if self.i >= len(self.string): raise StopIteration
        while self.string[self.i] == ' ': self.i += 1
        if self.regexp_end:
            self.regexp_end = False
            if self.string[self.i] in self.table:
                c = self.string[self.i]
                self.regexp_mod = True
                self.regexp_end = False
                self.i += 1
                return QueryLexeme(self.table[c], c)            
        if self.regexp_mod:
            self.regexp_mod = False
            if self.string[self.i] not in self.table:
                start = self.i
                while (self.i < len(self.string) and
                       self.string[self.i] not in self.table and
                       self.string[self.i] != ' '):
                    self.i += 1
                return QueryLexeme(REMODS, self.string[start:self.i])

        if self.regexp_start is not None:
            escaped = False
            s = ""
            try:
                while escaped or self.string[self.i] != self.regexp_start:
                    if not escaped and self.string[self.i] == '\\':
                        escaped = True
                    else:
                        if (escaped and
                            self.string[self.i] != self.regexp_start):
                            s += "\\"
                        escaped = False
                        s += self.string[self.i]
                    self.i += 1
            except IndexError:
                raise LexerError("A regular expression is not closed.")
            self.regexp_start = None
            self.regexp_end = True
            return QueryLexeme(RE, s)
        elif self.string[self.i] == '/':
            self.i += 1
            self.regexp_start = self.string[self.i - 1]
            return QueryLexeme(OPENRE, self.string[self.i - 1])
        elif self.string[self.i] in self.table:
            c = self.string[self.i]
            self.i += 1
            return QueryLexeme(self.table[c], c)
        else:
            start = self.i
            while (self.i < len(self.string) and
                   self.string[self.i] not in self.table.keys()):
                self.i += 1
            return QueryLexeme(TAG, self.string[start:self.i].strip())

class QueryLexeme(object):
    def __init__(self, typ, lexeme):
        self.type = typ
        self.lexeme = lexeme

    def __iter__(self):
        return iter((self.type, self.lexeme))

    def __repr__(self):
        return (object.__repr__(self).split()[0] +
                " type=" + repr(self.type) + " (" +
                str(QueryLexer._reverse[self.type]) +
                "), lexeme=" + repr(self.lexeme) + ">")

# Parse the input. One lookahead token, start symbol is Query.
class QueryParser(object):
    def __init__(self, tokens):
        self.lookahead = tokens.next()
        self.tokens = tokens

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
        return match.Numcmp(tag, op, value)

    def _match_string(self):
        s = self.lookahead.lexeme
        self.match(self.lookahead.type)
        return s

    def QueryPart(self):
        names = map(string.lower, self._match_list(self._match_string))
        self.match(EQUALS)
        res = self.RegexpSet()
        return match.Tag(names, res)

    def RegexpSet(self):
        if self.lookahead.type == UNION: return self.RegexpUnion()
        elif self.lookahead.type == INTERSECT: return self.RegexpInter()
        elif self.lookahead.type == NEGATION: return self.RegexpNeg()
        elif self.lookahead.type == OPENRE: return self.Regexp()
        else:
            raise ParseError("The expected symbol should be |, &, !, or "
                             "a tag name, but was %s" % self.lookahead.lexeme)


    def RegexpNeg(self):
        self.match(NEGATION)
        return match.Neg(self.Regexp())

    def RegexpUnion(self):
        return self._match_parened(UNION, match.Union, self.RegexpList)

    def RegexpInter(self):
        return self._match_parened(INTERSECT, match.Inter, self.RegexpList)

    def RegexpList(self):
        return self._match_list(self.RegexpSet)

    def Regexp(self):
        self.match(OPENRE)
        re = self.lookahead.lexeme
        mods = sre.IGNORECASE | sre.MULTILINE | sre.UNICODE
        self.match(RE)
        self.match(CLOSERE)
        if self.lookahead.type == REMODS:
            s = self.lookahead.lexeme.lower()
            if "c" in s: mods &= ~sre.IGNORECASE
            if "s" in s: mods |= sre.DOTALL
            if "l" in s: mods = (mods & ~sre.UNICODE) | sre.LOCALE
            self.match(REMODS)
        try: return sre.compile(re, mods)
        except sre.error:
            raise ParseError("The regular expression /%s/ is invalid." % re)

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

def parse(string):
    return QueryParser(QueryLexer(string)).StartQuery()

def is_valid(string):
    tokens = QueryLexer(string)
    try: QueryParser(tokens).StartQuery()
    except error: return False
    else: return True
