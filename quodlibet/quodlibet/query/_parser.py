# -*- coding: utf-8 -*-
import re

from . import _match as match
from ._match import error, ParseError
from ._diacritic import re_add_variants
from quodlibet.util import re_escape
        
# Precompiled regexes
TAG = re.compile(r'[~\w]+')
UNARY_OPERATOR = re.compile(r'-')
BINARY_OPERATOR = re.compile(r'[+\-\*/]')
RELATIONAL_OPERATOR = re.compile(r'>=|<=|==|!=|>|<|=')
DIGITS = re.compile(r'\d+(\.\d+)?')
WORD = re.compile(r'\w+')
REGEXP = re.compile(r'([^/\\]|\\.)*')
SINGLE_STRING = re.compile(r"([^'\\]|\\.)*")
DOUBLE_STRING = re.compile(r'([^"\\]|\\.)*')
MODIFIERS = re.compile(r'[cisld]*')
TEXT = re.compile(r'[^=)|&#/<>!@,]+')


class QueryParser(object):
    """Parse the input. One lookahead token, start symbol is Query."""

    def __init__(self, tokens, star=[]):
        self.tokens = tokens
        self.index = 0
        self.last_match = None
        self.star = star
        
    def lookahead(self, *tokens):
        try:
            return self.tokens[self.index] in tokens
        except IndexError:
            return False
        
    def space(self):
        while not self.eof() and self.tokens[self.index] == ' ':
            self.index += 1
        
    def accept(self, token, advance=True):
        self.space()
        if self.eof():
            return False
        if self.tokens[self.index] == token:
            if advance:
                self.index += 1
            return True
        else:
            return False
        
    def accept_re(self, regexp):
        self.space()
        re_match = regexp.match(self.tokens, self.index)
        if re_match:
            self.index = re_match.end()
            re_match = re_match.group()
        self.last_match = re_match
        return re_match
        
    def expect(self, token):
        if not self.accept(token):
            raise ParseError("'{0}' expected at index {1}, but not found"
                             .format(token, self.index))
        
    def expect_re(self, regexp):
        if self.accept_re(regexp) is None:
            raise ParseError("RE match expected at index {0}, but not found"
                             .format(self.index))
        return self.last_match
        
    def eof(self):
        return self.index >= len(self.tokens)
        
    def match_list(self, rule):
        m = [rule()]
        while self.accept(','):
            m.append(rule())
        return m

    def StartQuery(self):
        s = self.Query(outer=True)
        if not self.eof():
            raise ParseError('Query ended before end of input')
        return s

    def Query(self, outer=False):
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
            index = self.index
            return self.Equals()
        except ParseError:
            self.index = index
            return self.Star(outer=outer)
        
    def Negation(self, rule):
        return match.Neg(rule())
    
    def Intersection(self, rule):
        self.expect('(')
        inter = match.Inter(self.match_list(rule))
        self.expect(')')
        return inter
    
    def Union(self, rule):
        self.expect('(')
        union = match.Union(self.match_list(rule))
        self.expect(')')
        return union
    
    def Numcmp(self):
        cmps = []
        expr2 = self.Numexpr()
        while self.accept_re(RELATIONAL_OPERATOR):
            expr = expr2
            relop = self.last_match
            expr2 = self.Numexpr()
            cmps.append(match.Numcmp(expr, relop, expr2))
        if not cmps:
            raise ParseError('No relational operator in numerical comparison')
        return match.Inter(cmps)
    
    def Numexpr(self):
        if self.accept('('):
            expr = match.NumexprGroup(self.Numexpr())
            self.expect(')')
        if self.accept_re(UNARY_OPERATOR):
            expr = match.NumexprUnary(self.last_match, self.Numexpr())
        elif self.accept_re(DIGITS):
            number = float(self.last_match)
            if self.accept(':'):
                number2 = float(self.expect_re(DIGITS))
                expr = match.NumexprNumber(60*number, number2)
            elif self.accept_re(WORD):
                expr = match.numexprUnit(number, self.last_match)
            else:
                expr = match.NumexprNumber(number)
        else:
            expr = match.numexprTagOrSpecial(self.expect_re(TAG))
        if self.accept_re(BINARY_OPERATOR):
            binop = self.last_match
            expr2 = self.Numexpr()
            return match.NumexprBinary(binop, expr, expr2)
        else:
            return expr
        
    def Binexpr(self):
        expr = self.Numexpr()
        if self.accept_re(BINARY_OPERATOR):
            binop = self.last_match
            expr2 = self.Numexpr()
            return match.NumexprBinary(binop, expr, expr2)
        else:
            return expr
        
    def Extension(self):
        self.expect('(')
        name = self.expect_re(WORD)
        if self.accept(':'):
            body = self.ExtBody()
        else:
            body = None
        self.expect(')')
        return match.Extension(name, body)
    
    def ExtBody(self):
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
        tags = self.match_list(lambda:self.expect_re(TAG))
        self.expect('=')
        value = self.Value()
        return match.Tag(tags, value)
    
    def Value(self, outer=False):
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
            return self.RegexpMods(self.expect_re(TEXT))
        
    def RegexpMods(self, regex):
        mod_string = self.expect_re(MODIFIERS)
        mods = re.MULTILINE | re.UNICODE | re.IGNORECASE
        if "c" in mod_string:
            mods &= ~re.IGNORECASE
        if "i" in mod_string:
            mods |= re.IGNORECASE
        if "s" in mod_string:
            mods |= re.DOTALL
        if "l" in mod_string:
            mods = (mods & ~re.UNICODE) | re.LOCALE
        if "d" in mod_string:
            try:
                regex = re_add_variants(regex)
            except re.error:
                raise ParseError("The regular expression was invalid")
            except NotImplementedError:
                raise ParseError("The regular expression was is not supported")
        try:
            return re.compile(regex, mods)
        except re.error:
            raise ParseError("The regular expression /%s/ is invalid." % regex)
        
    def Star(self, outer=False):
        return match.Tag(self.star, self.Value(outer=outer))
        
    def str_to_re(self, string):
        if isinstance(string, unicode):
            string = string.encode('utf-8')
        string = string.decode('string_escape')
        string = string.decode('utf-8')
        return "^%s$" % re_escape(string)