#!/usr/bin/env python

import match
import sre

(NEGATION, INTERSECT, UNION, OPENP, CLOSEP, EQUALS, OPENRE,
 CLOSERE, REMODS, COMMA, TAG, RE, EOF) = range(13)

class QueryLexer(object):
    _reverse = { NEGATION: "NEGATION", INTERSECT: "INTERSECT",
                 OPENRE: "OPENRE", CLOSERE: "CLOSERE", REMODS: "REMODS",
                 OPENP: "OPENP", CLOSEP: "CLOSEP", UNION: "UNION",
                 EQUALS: "EQUALS", COMMA: "COMMA", TAG: "TAG", RE: "RE",
                 EOF: "EOF",
                 }

    table = { '!': NEGATION, '&': INTERSECT, '|': UNION,
              '(': OPENP, ')': CLOSEP, '=': EQUALS, ',': COMMA,
              ':': CLOSERE, '/': CLOSERE }

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
            while escaped or self.string[self.i] != self.regexp_start:
                if not escaped and self.string[self.i] == '\\':
                    escaped = True
                else:
                    escaped = False
                    s += self.string[self.i]
                self.i += 1
            self.regexp_start = None
            self.regexp_end = True
            return QueryLexeme(RE, s)
        elif self.string[self.i] == ':' or self.string[self.i] == '/':
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
                   self.string[self.i] not in ' ),=/'):
                self.i += 1
            return QueryLexeme(TAG, self.string[start:self.i])

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
        elif self.lookahead.type == TAG: return self.QueryPart()
        else: raise ValueError

    def QueryNeg(self):
        self.match(NEGATION)
        return match.Neg(self.Query())

    def QueryInter(self):
        return self._match_parened(INTERSECT, match.Inter, self.QueryList)

    def QueryUnion(self):
        return self._match_parened(UNION, match.Union, self.QueryList)

    def QueryList(self):
        return self._match_list(self.Query)

    def _match_string(self):
        s = self.lookahead.lexeme
        self.match(self.lookahead.type)
        return s

    def QueryPart(self):
        names = map(str.lower, self._match_list(self._match_string))
        self.match(EQUALS)
        res = self.RegexpSet()
        return match.Tag(names, res)

    def RegexpSet(self):
        if self.lookahead.type == UNION: return self.RegexpUnion()
        elif self.lookahead.type == INTERSECT: return self.RegexpInter()
        elif self.lookahead.type == NEGATION: return self.RegexpNeg()
        elif self.lookahead.type == OPENRE: return self.Regexp()
        else: raise ValueError

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
        mods = 0
        self.match(RE)
        self.match(CLOSERE)
        if self.lookahead.type == REMODS:
            s = self.lookahead.lexeme.lower()
            if "i" in s: mods |= sre.IGNORECASE
            if "s" in s: mods |= sre.DOTALL
            if "m" in s: mods |= sre.MULTILINE
            if "l" in s or "u" in s: mods |= sre.LOCALE
            self.match(REMODS)
        return sre.compile(re, mods)

    def match(self, token):
        if self.lookahead.type == EOF:
            raise ValueError("End of input!")
        try:
            if self.lookahead.type == token:
                self.lookahead = self.tokens.next()
            else:
                raise ValueError("Parse error!")
        except StopIteration:
            self.lookahead = QueryLexeme(EOF, "")

if __name__ == "__main__":
    import os.path, sys
    name = os.path.basename(__file__)
    name = "test_" + name
    if os.path.exists(name): os.execlp(sys.argv[0], sys.argv[0], name)
    else: print "W: No tests found for " + name[5:] + "."
#import sys
#while not sys.stdin.closed:
#    print repr(QueryParser(QueryLexer(sys.stdin.readline())).Query())

    
