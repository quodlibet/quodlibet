# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

# Pattern := (<String> | <Tags>)*
# String := ([^<>|\\]|\\.)+, a string
# Tags := "<" String [ "|" Pattern [ "|" Pattern ] ] ">"

# FIXME: We eventually want to be able to call these formatters in a
# tight loop, which isn't good if we're re-parsing the format string
# every time. The Song proxy might also get in the way.

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

class PatternParser(object):
    def __init__(self, tokens, func=lambda s, t: s.comma(t)):
        self.tokens = iter(tokens)
        self.lookahead = self.tokens.next()
        self.func = func

    def Pattern(self, song):
        text = []
        while self.lookahead.type in [OPEN, TEXT]:
            la = self.lookahead
            self.match(TEXT, OPEN)
            if la.type == TEXT: text.append(la.lexeme)
            elif la.type == OPEN: text.extend(self.Tags(song))
        return text

    def Tags(self, song):
        text = []
        all = []
        tag = self.lookahead.lexeme
        if not tag.startswith("~") and "~" in tag: tag = "~" + tag
        try: self.match(TEXT)
        except ParseError:
            while self.lookahead.type not in [CLOSE, EOF]:
                text.append(self.lookahead.lexeme)
                self.match(self.lookahead.type)
            all.append(u"".join(text))
            return all
        if self.lookahead.type == COND:
            self.match(COND)
            ifcase = self.Pattern(song)
            if self.lookahead.type == COND:
                self.match(COND)
                elsecase = self.Pattern(song)
            else: elsecase = u""

            if self.func(song, tag): all.extend(ifcase)
            else: all.extend(elsecase)

            try: self.match(CLOSE)
            except ParseError:
                all.pop(-1)
                text.append("<")
                parts = filter(None, [tag, ifcase, elsecase])
                for part in parts:
                    text.extend(part)
                    text.append("|")
                if parts: text.pop(-1)
                while self.lookahead.type not in [EOF, OPEN]:
                    text.append(self.lookahead.lexeme)
                    self.match(self.lookahead.type)
        else:
            if text:
                all.append(u"".join(text))
                text = []
            all.append(self.func(song, tag))
            try: self.match(CLOSE)
            except ParseError:
                all.pop(-1)
                text.append("<")
                text.append(tag)
                while self.lookahead.type not in [EOF, OPEN]:
                    text.append(self.lookahead.lexeme)
                    self.match(self.lookahead.type)
        if text:
            all.append(u"".join(text))
            text = []
        return all

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

class _Pattern(PatternParser):
    _formatters = []

    def __init__(self, string):
        self.__string = string
        self.__tokens = list(PatternLexer(self.__string))
        self.format(_Dummy()) # Validate string

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.__string)

    class Song(object):
        def __init__(self, realsong, formatters):
            self.__song = realsong
            self.__formatters = formatters
            self.__cache = {}

        def comma(self, key):
            if key in self.__cache:
                return self.__cache[key]
            value = self.__song.comma(key)
            if isinstance(value, str):
                value = util.fsdecode(value)
            elif not isinstance(value, unicode):
                value = unicode(value)
            for f in self.__formatters:
                value = f(key, value)
            self.__cache[key] = value
            return value

        def list_separate(self, key):
            if key.startswith("~#") and "~" not in key[2:]:
                values = [unicode(self.__song(key))]
            else: values = self.__song.list_separate(key)
            for f in self.__formatters:
                values = map(lambda v: f(key, v), values)
            return values

    def format(self, song):
        p = PatternParser(self.__tokens)
        vals = p.Pattern(self.Song(song, self._formatters))
        return self._post(u"".join(vals), song)

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
        p = PatternParser(self.__tokens, lambda s, t: s.list_separate(t))
        vals = expand(p.Pattern(self.Song(song, self._formatters)))
        return [self._post(v, song) for v in vals]

    def real_tags(self, cond=True):
        tags = []
        tokens = self.__tokens
        for i, tok in enumerate(tokens):
            if tok.type == TEXT and \
                tokens[max(0, i-1)].type == OPEN and \
                tokens[i+1].type != EOF and \
                (tokens[i+1].type != COND or cond):
                tags.extend(util.tagsplit(tok.lexeme))
        return [t for i, t in enumerate(tags) if i == tags.index(t)]

    def _post(self, value, song): return value

    __mod__ = format

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

class _FileFromPattern(_Pattern):
    _formatters = [_number,
                   (lambda k, s: s.lstrip(".")),
                   (lambda k, s: s.replace("/", "_")),
                   (lambda k, s: s.replace(u"\uff0f", "_")),
                   (lambda k, s: s.strip()),
                   (lambda k, s: (len(s) > 100 and s[:100] + "...") or s),
                   ]

    def __init__(self, string):
        # On Windows, users may use backslashes in patterns as path separators.
        # Since Windows filenames can't use '<>|' anyway, preserving backslash
        # escapes is unnecessary, so we just replace them blindly.
        if os.name == 'nt':
            string = string.replace("\\", "/")
        super(_FileFromPattern, self).__init__(string)

    def _post(self, value, song):
        if value:
            fn = song.get("~filename", ".")
            ext = fn[fn.rfind("."):].lower()
            val_ext = value[-len(ext):].lower()
            if not ext == val_ext: value += ext.lower()
            value = os.path.expanduser(value)
            if "/" in value and not os.path.isabs(value):
                raise ValueError("Pattern is not rooted")
        return value

class _XMLFromPattern(_Pattern):
    _formatters = [lambda k, s: util.escape(s)]

def Pattern(string, Kind=_Pattern, MAX_CACHE_SIZE=100, cache={}):
    if (Kind, string) not in cache:
        if len(cache) > MAX_CACHE_SIZE:
            cache.clear()
        cache[(Kind, string)] = Kind(string)
    return cache[(Kind, string)]

def FileFromPattern(string):
    return Pattern(string, _FileFromPattern)

def XMLFromPattern(string):
    return Pattern(string, _XMLFromPattern)
