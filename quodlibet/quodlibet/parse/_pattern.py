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
        return "Text(\"%s\")" % self.text

class ConditionNode(object):
    def __init__(self, tag, ifcase, elsecase):
        self.tag = tag
        self.ifcase = ifcase
        self.elsecase = elsecase

    def __repr__(self):
        t, i, e = self.tag, repr(self.ifcase), repr(self.elsecase)
        return "Condition(tag: \"%s\", if: %s, else: %s)" % (t, i, e)

class TagNode(object):
    def __init__(self, tag):
        self.tag = tag

    def __repr__(self):
        return "Tag(\"%s\")" % self.tag

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

class PatternFormatter(object):
    _formatters = []
    _post = None

    def __init__(self, func, list_func, tags):
        self.__func = func
        self.__list_func = list_func
        self.tags = set(tags)
        self.format(self.Dummy()) # Validate string

    class Dummy(dict):
        def comma(self, *args): return u"_"
        def list_separate(self, *args): return [u""]

    class SongProxy(object):
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
                values = [f(key, v) for v in values]
            return values

    def format(self, song):
        value = "".join(self.__func(self.SongProxy(song, self._formatters)))
        if self._post:
            return self._post(value, song)
        return value

    def format_list(self, song):
        """Returns a set of formatted patterns with all tag combinations:
        <performer>-bla returns [performer1-bla, performer2-bla]"""
        vals = [""]
        for val in self.__list_func(self.SongProxy(song, self._formatters)):
            if type(val) == list:
                vals = [r + part for part in val for r in vals]
            else:
                vals = [r + val for r in vals]
        if self._post:
            return set([self._post(v, song) for v in vals])
        return set(vals)

    __mod__ = format

class PatternCompiler(object):
    def __init__(self, root):
        self.__root = root.node

    def compile(self, song_func):
        tags = set()
        content = [
            "def f(s):",
            "  x = s." + song_func,
            "  r = []",
            "  a = r.append"]
        content.extend(self.__pattern(self.__root, {}, tags))
        content.append("  return r")
        code = "\n".join(content)

        scope = {}
        exec compile(code, "<string>", "exec") in scope
        return scope["f"], tags

    def __escape(self, text):
        text = text.replace("\\", r"\\")
        text = text.replace("\"", "\\\"")
        return text.replace("\n", r"\n")

    def __put_tag(self, text, scope, tag):
        tag = self.__escape(tag)
        if tag not in scope:
            scope[tag] = 't%d' % len(scope)
            text.append('%s = x("%s")' % (scope[tag], tag))
        return tag

    def __tag(self, node, scope, tags):
        text = []
        if isinstance(node, TextNode):
            text.append('a("%s")' % self.__escape(node.text))
        elif isinstance(node, ConditionNode):
            tag = self.__put_tag(text, scope, node.tag)
            ic = self.__pattern(node.ifcase, dict(scope), tags)
            ec = self.__pattern(node.elsecase, dict(scope), tags)
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
            tags.update(util.tagsplit(node.tag))
            tag = self.__put_tag(text, scope, node.tag)
            text.append('a(%s)' % scope[tag])
        return text

    def __pattern(self, node, scope, tags):
        text = []
        if isinstance(node, PatternNode):
            for child in node.children:
                text.extend(self.__tag(child, scope, tags))
        return map("  ".__add__, text)

def Pattern(string, Kind=PatternFormatter, MAX_CACHE_SIZE=100, cache={}):
    if (Kind, string) not in cache:
        if len(cache) > MAX_CACHE_SIZE:
            cache.clear()
        comp = PatternCompiler(PatternParser(PatternLexer(string)))
        func, tags = comp.compile("comma")
        list_func, tags = comp.compile("list_separate")
        cache[(Kind, string)] = Kind(func, list_func, tags)
    return cache[(Kind, string)]

def _number(key, value):
    if key == "tracknumber":
        parts = value.split("/")
        try: decimals = len(str(int(parts[1])))
        except (IndexError, ValueError): decimals = 2
        try: return "%0*d" % (max(2, decimals), int(parts[0]))
        except (TypeError, ValueError): return value
    elif key == "discnumber":
        parts = value.split("/")
        try: return "%02d" % int(parts[0])
        except (TypeError, ValueError): return value
    else: return value

class _FileFromPattern(PatternFormatter):
    _formatters = [_number,
                   (lambda k, s: s.replace(os.sep, "_")),
                   (lambda k, s: s.replace(u"\uff0f", "_")),
                   (lambda k, s: s.strip()),
                   ]

    def _post(self, value, song):
        if value:
            fn = song.get("~filename", ".")
            ext = fn[fn.rfind("."):].lower()
            val_ext = value[-len(ext):].lower()
            if not ext == val_ext: value += ext.lower()
            if os.name == "nt":
                value = util.strip_win32_incompat_from_path(value)

            value = util.expanduser(value)

            # Limit each path section to 255 (bytes on linux, chars on win).
            # http://en.wikipedia.org/wiki/Comparison_of_file_systems#Limits
            path, ext = os.path.splitext(value)
            path = map(util.fsnative, path.split(os.sep))
            limit = [255] * len(path)
            limit[-1] -= len(util.fsnative(ext))
            elip = lambda (p, l): (len(p) > l and p[:l-2] + "..") or p
            path = os.sep.join(map(elip, zip(path, limit)))
            value = util.fsdecode(path) + ext

            if os.sep in value and not os.path.isabs(value):
                raise ValueError("Pattern is not rooted")
        return value

class _XMLFromPattern(PatternFormatter):
    _formatters = [lambda k, s: util.escape(s)]


def FileFromPattern(string):
    # On Windows, users may use backslashes in patterns as path separators.
    # Since Windows filenames can't use '<>|' anyway, preserving backslash
    # escapes is unnecessary, so we just replace them blindly.
    if os.name == 'nt':
        string = string.replace("\\", r"\\")
    return Pattern(string, _FileFromPattern)

def XMLFromPattern(string):
    return Pattern(string, _XMLFromPattern)
