# Copyright 2004-2010 Joe Wreschnig, Michael Urman, Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

# Pattern := (<String> | <Tags>)*
# String := ([^<>|\\]|\\.)+, a string
# Tags := "<" String [ "|" Pattern [ "|" Pattern ] ] ">"

import os
import re

from quodlibet import util
from quodlibet.parse._scanner import Scanner

class _Dummy(dict):
    def comma(self, *args): return u"_"
    def list_separate(self, *args): return [u""]

# Token types.
(OPEN, CLOSE, TEXT, COND, EOF) = range(5)

class error(ValueError): pass
class ParseError(error): pass
class LexerError(error): pass

class PatternLexeme(object):
    _reverse = { OPEN: "OPEN", CLOSE: "CLOSE", TEXT: "TEXT", COND: "COND",
                 EOF: "EOF" }

    def __init__(self, typ, lexeme):
        self.type = typ
        self.lexeme = lexeme

    def __repr__(self):
        return (super(PatternLexeme, self).__repr__().split()[0] +
                " type=" + repr(self.type) + " (" +
                str(self._reverse[self.type]) +
                "), lexeme=" + repr(self.lexeme) + ">")

class PatternLexer(Scanner):
    def __init__(self, s):
        self.string = s.strip()
        Scanner.__init__(self,
                         [(r"([^<>|\\]|\\.)+", self.text),
                          (r"[<>|]", self.table),
                          ])

    def text(self, scanner, string):
        return PatternLexeme(TEXT, re.sub(r"\\(.)", r"\1", string))
    def table(self, scanner, string):
        return PatternLexeme(
            {"|": COND, "<": OPEN, ">": CLOSE}[string], string)

    def __iter__(self):
        s = self.scan(self.string)
        if s[1] != "": raise LexerError("characters left over in string")
        else: return iter(s[0] + [PatternLexeme(EOF, "")])

class PatternNode(object):
    def __init__(self):
        self.children = []

    def __repr__(self):
        return "Pattern(%s)" % (", ".join(map(repr, self.children)))

class TextNode(object):
    def __init__(self, text):
        self.text = text

    def __repr__(self):
        return "Text(%s)" % self.text

class ConditionNode(object):
    def __init__(self, tag, ifcase, elsecase):
        self.tag = tag
        self.ifcase = ifcase
        self.elsecase = elsecase

    def __repr__(self):
        t, i, e = self.tag, repr(self.ifcase), repr(self.elsecase)
        return "Condition(tag:%s, if: %s, else: %s)" % (t, i, e)

class TagNode(object):
    def __init__(self, tag):
        self.tag = tag

    def __repr__(self):
        return "Tag(%s)" % self.tag

class PatternParser(object):
    def __init__(self, tokens):
        self.tokens = iter(tokens)
        self.lookahead = self.tokens.next()
        self.node = self.Pattern()

    def Pattern(self):
        node = PatternNode()
        while self.lookahead.type in [OPEN, TEXT]:
            la = self.lookahead
            self.match(TEXT, OPEN)
            if la.type == TEXT:
                node.children.append(TextNode(la.lexeme))
            elif la.type == OPEN:
                node.children.extend(self.Tags())
        return node

    def Tags(self):
        nodes = []
        tag = self.lookahead.lexeme
        # fix bad tied tags
        if tag[:1] != "~" and "~" in tag:
                tag = "~" + tag
        try: self.match(TEXT)
        except ParseError:
            while self.lookahead.type not in [CLOSE, EOF]:
                self.match(self.lookahead.type)
            return nodes
        if self.lookahead.type == COND:
            self.match(COND)
            ifcase = self.Pattern()
            if self.lookahead.type == COND:
                self.match(COND)
                elsecase = self.Pattern()
            else: elsecase = None
            nodes.append(ConditionNode(tag, ifcase, elsecase))

            try: self.match(CLOSE)
            except ParseError:
                nodes.pop(-1)
                while self.lookahead.type not in [EOF, OPEN]:
                    self.match(self.lookahead.type)
        else:
            nodes.append(TagNode(tag))
            try: self.match(CLOSE)
            except ParseError:
                nodes.pop(-1)
                while self.lookahead.type not in [EOF, OPEN]:
                    self.match(self.lookahead.type)
        return nodes

    def match(self, *tokens):
        if tokens != [EOF] and self.lookahead.type == EOF:
            raise ParseError("The search string ended, but more "
                             "tokens were expected.")
        try:
            if self.lookahead.type in tokens:
                self.lookahead = self.tokens.next()
            else:
                raise ParseError("The token '%s' is not the type exected." %(
                    self.lookahead.lexeme))
        except StopIteration:
            self.lookahead = PatternLexeme(EOF, "")

class PatternCompiler(object):
    _formatters = []

    def __init__(self, root_node):
        self.__count = 0
        self.tags = set()
        self.__root = root_node
        self.__func = self.__compile("comma")
        self.__list_func = self.__compile("list_separate")
        self.format(_Dummy()) # Validate string

    class Song(object):
        def __init__(self, realsong, formatters):
            self.__song = realsong
            self.__formatters = formatters

        def comma(self, key):
            value = self.__song.comma(key)
            if isinstance(value, str):
                value = util.fsdecode(value)
            elif not isinstance(value, unicode):
                if isinstance(value, float):
                    value = "%.2f" % value
                value = unicode(value)
            for f in self.__formatters:
                value = f(key, value)
            return value

        def list_separate(self, key):
            if key.startswith("~#") and "~" not in key[2:]:
                value = self.__song(key)
                if isinstance(value, float):
                    value = "%.2f" % value
                values = [unicode(value)]
            else: values = self.__song.list_separate(key)
            for f in self.__formatters:
                values = map(lambda v: f(key, v), values)
            return values

    def _post(self, value, song):
        return value

    def format(self, song):
        proxy = self.Song(song, self._formatters)
        return self._post(u"".join(self.__func(proxy)), song)

    def format_list(self, song):
        """Returns a list of formated patterns with all tag combinations:
        <performer>-bla returns [performer1-bla, performer2-bla]"""
        def expand(values):
            results = []
            for val in values:
                if type(val) == list:
                    new_results = []
                    for r in (results or [u""]):
                        for part in val:
                            new_results.append(r + part)
                    results = new_results
                else:
                    results = [r + val for r in (results or [u""])]
            return results
        proxy = self.Song(song, self._formatters)
        vals = expand(self.__list_func(proxy))
        return [self._post(v, song) for v in vals]

    __mod__ = format

    def __compile(self, song_func):
        self.__count = 0
        self.tags.clear()
        content = [
            "def f(s):",
            "  r = []",
            "  x = s." + song_func,
            "  a = r.append"]
        content.extend(self.__pattern(self.__root, {}))
        content.append("  return r")
        code = "\n".join(content)
        exec compile(code, "<string>", "exec")
        return f

    def __escape(self, text):
        return text.replace("\"", "\\\"").replace("\n", r"\n")

    def __put_tag(self, text, scope, tag):
        tag = self.__escape(tag)
        if tag not in scope:
            text.append('t%d = x("%s")' % (self.__count, tag))
            scope[tag] = 't%d' % self.__count
            self.__count += 1
        return tag

    def __tag(self, node, scope):
        scope = dict(scope)
        text = []
        if isinstance(node, TextNode):
            text.append('a("%s")' % self.__escape(node.text))
        elif isinstance(node, ConditionNode):
            tag = self.__put_tag(text, scope, node.tag)
            ic = self.__pattern(node.ifcase, scope)
            ec = self.__pattern(node.elsecase, scope)
            if not ic and not ec:
                text.pop(-1)
            elif ic:
                text.append('if %s:' % scope[tag])
                text.extend(ic)
                if ec:
                    text.append('else:')
                    text.extend(ec)
            else:
                text.append('if not %s:' % scope[tag])
                text.extend(ec)
        elif isinstance(node, TagNode):
            self.tags.update(util.tagsplit(node.tag))
            tag = self.__put_tag(text, scope, node.tag)
            text.append('a(%s)' % scope[tag])
        return text

    def __pattern(self, node, scope):
        scope = dict(scope)
        text = []
        if isinstance(node, PatternNode):
            for child in node.children:
                text.extend(self.__tag(child, scope))
        return map(lambda x: "  " + x, text)

def Pattern(string, Kind=PatternCompiler, MAX_CACHE_SIZE=100, cache={}):
    if (Kind, string) not in cache:
        if len(cache) > MAX_CACHE_SIZE:
            cache.clear()
        tokens = PatternLexer(string)
        tree = PatternParser(tokens)
        cache[(Kind, string)] = Kind(tree.node)
    return cache[(Kind, string)]

def _number(key, value):
    if key == "tracknumber":
        parts = value.split("/")
        try: return "%02d" % int(parts[0])
        except (TypeError, ValueError): return value
    elif key == "discnumber":
        parts = value.split("/")
        try: return "%02d" % int(parts[0])
        except (TypeError, ValueError): return value
    else: return value

class _FileFromPattern(PatternCompiler):
    _formatters = [_number,
                   (lambda k, s: s.lstrip(".")),
                   (lambda k, s: s.replace("/", "_")),
                   (lambda k, s: s.replace(u"\uff0f", "_")),
                   (lambda k, s: s.strip()),
                   (lambda k, s: (len(s) > 100 and s[:100] + "...") or s),
                   ]

    def _post(self, value, song):
        if value:
            fn = song.get("~filename", ".")
            ext = fn[fn.rfind("."):].lower()
            val_ext = value[-len(ext):].lower()
            if not ext == val_ext: value += ext.lower()
            value = util.expanduser(value)
            #FIXME: windows
            if "/" in value and not os.path.isabs(value):
                raise ValueError("Pattern is not rooted")
        return value

class _XMLFromPattern(PatternCompiler):
    _formatters = [lambda k, s: util.escape(s)]


def FileFromPattern(string):
    # On Windows, users may use backslashes in patterns as path separators.
    # Since Windows filenames can't use '<>|' anyway, preserving backslash
    # escapes is unnecessary, so we just replace them blindly.
    if os.name == 'nt':
        string = string.replace("\\", "/")
    return Pattern(string, _FileFromPattern)

def XMLFromPattern(string):
    return Pattern(string, _XMLFromPattern)
