# -*- coding: utf-8 -*-
import re

from . import _match as match
from ._match import error, ParseError
from ._diacritic import re_add_variants
from quodlibet.util import re_escape


class QueryParser(object):
    """Parse the input. One lookahead token, start symbol is Query."""
        
    TAG = re.compile(r'[~\w+]+')
    UNARY_OPERATOR = re.compile(r'-')
    BINARY_OPERATOR = re.compile(r'[+-\*/]')
    RELATIONAL_OPERATOR = re.compile(r'>|<|=|>=|<=|==|!=')
    DIGITS = re.compile(r'\d+')
    WORD = re.compile(r'\w+')
    REGEXP = re.compile(r'([^/\\]|\\.)*')
    SINGLE_STRING = re.compile(r"([^'\\]|\\.)*")
    DOUBLE_STRING = re.compile(r'([^"\\]|\\.)*')
    MODIFIERS = re.compile(r'[cisld]*')
    TEXT = re.compile(r'[^,)]*')

    def __init__(self, tokens):
        self.tokens = tokens
        self.index = 0
        self.last_match = None
        
    def lookahead(self):
        return self.tokens[self.index]
        
    def space(self):
        while self.lookahead() == ' ':
            self.index += 1
        
    def accept(self, *tokens):
        self.space()
        try:
            if self.lookahead() in tokens:
                self.index += 1
                return True
            else:
                return False
        except IndexError:
            return False
        
    def accept_re(self, regexp):
        self.space()
        re_match = regexp.match(self.tokens, self.index)
        if re_match:
            self.index = re_match.end()
        self.last_match = re_match
        return re_match
        
    def expect(self, *tokens):
        if not self.accept(tokens):
            raise ParseError("'{0}' expected at index {1}, but not found")
        
    def expect_re(self, regexp):
        re_match = self.accept_re(regexp)
        if not re_match:
            raise ParseError("'{0}' expected at index {1}, but not found")
        return re_match
        
    def eof(self):
        return self.index >= len(self.tokens)
        
    def match_list(self, rule):
        self.expect('(')
        m = [rule()]
        while self.accept(','):
            m.append(rule())
        self.expect(')')
        return m

    def Query(self):
        if self.eof():
            return match.True_()
        elif self.accept('!'):
            return self.Negation(self.Query)
        elif self.accept('&'):
            return self.Intersection(self.Query)
        elif self.accept('|'):
            return self.Union(self.Query)
        elif self.accept('#'):
            return self.Numcmp()
        elif self.accept('@'):
            return self.Extension()
        try:
            return self.Equals()
        except ParseError:
            return self.Value()
        
    def Negation(self, rule):
        return match.Neg(rule())
    
    def Intersection(self, rule):
        return match.Inter(self.match_list(self, rule))
    
    def Union(self, rule):
        return match.Union(self.match_list(self, rule))
    
    #TODO new match.Numcmp semantics
    def Numcmp(self):
        cmps = []
        self.expect('(')
        expr2 = self.Numexpr()
        while self.accept_re(RELATIONAL_OPERATOR):
            expr = expr2
            relop = self.last_match.group()
            expr2 = self.Numexpr()
            cmps.append(match.Numcmp(expr, relop, expr2))
        if not cmps:
            raise ParseError('No relational operator in numerical comparison')
        self.expect(')')
        return match.Inter(cmps)
    
    def Numexpr(self):
        if self.accept('('):
            expr = match.NumexprGroup(self.Numexpr())
            self.expect(')')
        if self.accept_re(UNARY_OPERATOR):
            expr = match.NumexprUnary(self.last_match, self.Numexpr())
        elif self.accept_re(TAG):
            expr = match.numexprTagOrSpecial(self.last_match)
        else:
            number = float(self.expect_re(DIGITS).group())
            if self.accept(':'):
                number2 = float(self.expect_re(DIGITS).group())
                expr = match.NumexprNumber(60*number, number2)
            elif self.accept_re(WORD):
                expr = match.numexprUnit(number, self.last_match)
            else:
                expr = match.NumexprNumber(number)
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
        name = self.expect_re(WORD).group()
        if self.accept(':'):
            body = self.ExtBody()
        else:
            body = None
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
                elif current = '\\':
                    index += 1
                index += 1
        except IndexError:
            if depth != 0:
                raise ParseError('Unexpected end of string while parsing extension body')
        result = self.tokens[self.index:index]
        self.index = index
        return tokens
        
    def Equals(self):
        tag = self.expect_re(TAG)
        self.expect('=')
        value = self.Value()
        return match.Tag([tag], value)
    
    def Value(self):
        if self.lookahead() in '/\'"':
            return self.Regexp()
        elif self.accept('!'):
            return self.Negation(self.Value)
        elif self.accept('|'):
            return self.Union(self.Value)
        elif self.accept('&'):
            return self.Intersection(self.Value)
        else:
            return match.star(self.expect_re(TEXT))
        
    def Regexp(self):
        if self.accept('/'):
            regex = self.expect_re(REGEXP).group()
            self.expect('/')
        elif self.accept('"'):
            regex = self.str_to_re(self.expect_re(DOUBLE_STRING).group())
            self.expect('"')
        elif self.accept("'"):
            regex = self.str_to_re(self.expect_re(SINGLE_STRING).group())
            self.expect("'")
        mod_string = expect_re(MODIFIERS).group()
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
        
    def str_to_re(self, string):
        if isinstance(string, unicode):
            string = string.encode('utf-8')
        string = string[1:-1].decode('string_escape')
        string = string.decode('utf-8')
        return "^%s$" % re_escape(string)