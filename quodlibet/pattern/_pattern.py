# Copyright 2004-2010 Joe Wreschnig, Michael Urman
# Copyright 2010,2013 Christoph Reiter
# Copyright 2013-2025 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# Pattern := (<String> | <Tags>)*
# String := ([^<>|\\]|\\.)+, a string
# Tags := "<" String [ "|" Pattern [ "|" Pattern ] ] ">"

import os
import re
from collections import OrderedDict
from re import Scanner  # type: ignore
from urllib.parse import quote_plus

from senf import fsnative

from quodlibet import util
from quodlibet.query import Query
from quodlibet.util.path import strip_win32_incompat_from_path, limit_path
from quodlibet.formats._audio import decode_value, FILESYSTEM_TAGS

# Token types.
(OPEN, CLOSE, TEXT, COND, EOF, DISJ) = range(6)


class Error(ValueError):
    pass


class ParseError(Error):
    pass


class LexerError(Error):
    pass


class PatternLexeme:
    _reverse = {
        OPEN: "OPEN",
        CLOSE: "CLOSE",
        TEXT: "TEXT",
        COND: "COND",
        EOF: "EOF",
        DISJ: "DISJ",
    }

    def __init__(self, typ, lexeme):
        self.type = typ
        self.lexeme = lexeme

    def __repr__(self):
        return (
            super().__repr__().split()[0]
            + " type="
            + repr(self.type)
            + " ("
            + str(self._reverse[self.type])
            + "), lexeme="
            + repr(self.lexeme)
            + ">"
        )


class PatternLexer(Scanner):
    def __init__(self, s):
        self.string = s
        Scanner.__init__(
            self,
            [
                (r"(?:[^<>|\\]|\\.)+", self.text),
                (r"\|\||[<>|]", self.table),
            ],
        )

    def text(self, scanner, string):
        return PatternLexeme(TEXT, re.sub(r"\\([|<>\\])", r"\1", string))

    def table(self, scanner, string):
        return PatternLexeme(
            {"||": DISJ, "|": COND, "<": OPEN, ">": CLOSE}[string], string
        )

    def __iter__(self):
        s = self.scan(self.string)
        if s[1] != "":
            raise LexerError("characters left over in string")
        return iter(s[0] + [PatternLexeme(EOF, "")])


class PatternNode:
    def __init__(self):
        self.children = []

    def __repr__(self):
        return "Pattern({})".format(", ".join(map(repr, self.children)))


class TextNode:
    def __init__(self, text):
        self.text = text

    def __repr__(self):
        return f'Text("{self.text}")'


class ConditionNode:
    def __init__(self, expr, ifcase, elsecase):
        self.expr = expr
        self.ifcase = ifcase
        self.elsecase = elsecase

    def __repr__(self):
        t, i, e = self.expr, repr(self.ifcase), repr(self.elsecase)
        return f'Condition(expression: "{t}", if: {i}, else: {e})'


class DisjunctionNode:
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def __repr__(self):
        nlrepr = repr([repr(node) for node in self.nodelist])
        return f"Disjunction({nlrepr})"


class TagNode:
    def __init__(self, tag):
        self.tag = tag

    def __repr__(self):
        return f'Tag("{self.tag}")'


class PatternParser:
    def __init__(self, tokens):
        self.tokens = iter(tokens)
        self.lookahead = next(self.tokens)
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
        first_node = None
        try:
            if self.lookahead.type == OPEN:
                first_node = self.Pattern()
            else:
                self.match(TEXT)
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
            else:
                elsecase = None
            nodes.append(ConditionNode(tag, ifcase, elsecase))

            try:
                self.match(CLOSE)
            except ParseError:
                nodes.pop(-1)
                while self.lookahead.type not in [EOF, OPEN]:
                    self.match(self.lookahead.type)
        elif self.lookahead.type == DISJ and first_node:
            nodelist = [first_node]
            while self.lookahead.type == DISJ:
                self.match(DISJ)
                nodelist.append(self.Pattern())
            nodes.append(DisjunctionNode(nodelist))

            try:
                self.match(CLOSE)
            except ParseError:
                nodes.pop(-1)
                while self.lookahead.type not in [EOF, OPEN]:
                    self.match(self.lookahead.type)
        else:
            nodes.append(TagNode(tag))
            try:
                self.match(CLOSE)
            except ParseError:
                nodes.pop(-1)
                while self.lookahead.type not in [EOF, OPEN]:
                    self.match(self.lookahead.type)
        return nodes

    def match(self, *tokens):
        if tokens != [EOF] and self.lookahead.type == EOF:
            raise ParseError("The search string ended, but more tokens were expected.")
        try:
            if self.lookahead.type in tokens:
                self.lookahead = next(self.tokens)
            else:
                raise ParseError(
                    f"The token '{self.lookahead.lexeme}' is not the type expected."
                )
        except StopIteration:
            self.lookahead = PatternLexeme(EOF, "")


class PatternFormatter:
    _format = None
    _post = None
    _text = None

    def __init__(self, func, list_func, tags):
        self.__func = func
        self.__list_func = list_func
        self.tags = util.list_unique(tags)
        self.format(self.Dummy())  # Validate string

    class Dummy(dict):
        def __call__(self, key, *args):
            if key in FILESYSTEM_TAGS:
                return fsnative("_")
            if key[:2] == "~#" and "~" not in key[2:]:
                return 0
            return "_"

        def comma(self, key, *args):
            return "_"

        def list_separate(self, key):
            return [""]

    class SongProxy:
        def __init__(self, realsong, formatter):
            self.__song = realsong
            self.__formatter = formatter

        def __call__(self, key, *args):
            return self.__song(key, *args)

        def get(self, key, default=None):
            return self.__song.get(key, default)

        def comma(self, key):
            value = self.__song.comma(key)
            if isinstance(value, int | float):
                value = decode_value(key, value)
            if self.__formatter:
                return self.__formatter(key, value)
            return value

        def list_separate(self, key):
            if key.startswith("~#") and "~" not in key[2:]:
                value = self.__song(key)
                value = decode_value(key, value)
                if self.__formatter:
                    value = self.__formatter(key, value)
                values = [(value, value)]
            else:
                values = self.__song.list_separate(key)
                if self.__formatter:
                    return [
                        (self.__formatter(key, v[0]), self.__formatter(key, v[1]))
                        for v in values
                    ]

            return values

    def format(self, song):
        value = "".join(self.__func(self.SongProxy(song, self._format)))
        if self._post:
            return self._post(value, song)
        return value

    def format_list(self, song):
        """Formats the output of a list pattern, generating all the
        combinations always returns pairs of display and sort values. The
        returned set will never be empty (e.g. for an empty pattern).
        """
        vals = [("", "")]
        for val in self.__list_func(self.SongProxy(song, self._format)):
            if not val:
                continue
            if isinstance(val, list):  # list of strings or pairs
                vals = [(r[0] + part[0], r[1] + part[1]) for part in val for r in vals]
            else:  # just a display string to concatenate
                vals = [(r[0] + val, r[1] + val) for r in vals]

        if self._post:
            vals = ((self._post(v[0], song), self._post(v[1], song)) for v in vals)
        return set(vals)

    __mod__ = format


class PatternCompiler:
    def __init__(self, root):
        self.__root = root.node

    def compile(self, song_func, text_formatter=None):
        tags = []
        queries = {}
        content = ["def f(s):", "  x = s." + song_func, "  r = []", "  a = r.append"]
        content.extend(self.__tag(self.__root, {}, {}, tags, queries, text_formatter))
        content.append("  return r")
        code = "\n".join(content)

        scope = dict(queries.values())
        if text_formatter:
            scope["_format"] = text_formatter
        exec(compile(code, "<string>", "exec"), scope)
        return scope["f"], tags

    def __get_value(self, text, scope, tag):
        if tag not in scope:
            t_var = "v%d" % len(scope)
            scope[tag] = t_var
            text.append(f"{t_var} = x({tag!r})")
        else:
            t_var = scope[tag]
        return t_var

    def __get_query(self, text, scope, qscope, query, queries):
        if query not in qscope:
            if query in queries:
                q_var = queries[query][0]
                r_var = "r%d" % len(qscope)
                text.append(f"{r_var} = {q_var}(s)")
                qscope[query] = r_var
            else:
                q = Query.StrictQueryMatcher(query)
                if q is not None:
                    q_var = "q%d" % len(queries)
                    r_var = "r%d" % len(qscope)
                    queries[query] = (q_var, q.search)
                    text.append(f"{r_var} = {q_var}(s)")
                    qscope[query] = r_var
                else:
                    r_var = self.__get_value(text, scope, query)
        else:
            r_var = qscope[query]
        return r_var

    def __tag(self, node, scope, qscope, tags, queries, text_formatter):
        text = []
        if isinstance(node, TextNode):
            if text_formatter:
                text.append(f"a(_format({node.text!r}))")
            else:
                text.append(f"a({node.text!r})")
        elif isinstance(node, ConditionNode):
            var = self.__get_query(text, scope, qscope, node.expr, queries)
            ic = self.__tag(
                node.ifcase, dict(scope), dict(qscope), tags, queries, text_formatter
            )
            ec = self.__tag(
                node.elsecase, dict(scope), dict(qscope), tags, queries, text_formatter
            )
            if not ic and not ec:
                text.pop(-1)
            elif ic:
                text.append(f"if {var}:")
                text.extend(ic)
                if ec:
                    text.append("else:")
                    text.extend(ec)
            else:
                text.append(f"if not {var}:")
                text.extend(ec)
        elif isinstance(node, DisjunctionNode):
            text.append("while True:")
            text.append("  r_len = len(r)")
            for n in node.nodelist:
                tag = self.__tag(
                    n, dict(scope), dict(qscope), tags, queries, text_formatter
                )
                text.extend(tag)
                non_empty_or_pop = [
                    "  if len(r) > r_len:",
                    "    if r[-1]:",
                    "       break",
                    "    r.pop()",
                ]
                text.extend(non_empty_or_pop)
            text.append("  break")
        elif isinstance(node, TagNode):
            tags.extend(util.tagsplit(node.tag))
            var = self.__get_value(text, scope, node.tag)
            text.append(f"a({var})")
        elif isinstance(node, PatternNode):
            for child in node.children:
                for line in self.__tag(
                    child, scope, qscope, tags, queries, text_formatter
                ):
                    text.append("  " + line)
        return text


def Pattern(string, formatter_cls=PatternFormatter, max_cache_size=100, cache=None):
    if cache is None:
        cache = OrderedDict()
    if (formatter_cls, string) not in cache:
        while len(cache) >= max_cache_size:
            cache.popitem(last=False)
        comp = PatternCompiler(PatternParser(PatternLexer(string)))
        func, tags = comp.compile("comma", formatter_cls._text)
        list_func, tags = comp.compile("list_separate", formatter_cls._text)
        cache[(formatter_cls, string)] = formatter_cls(func, list_func, tags)
    else:
        # promote recently accessed items to front of cache
        cache.move_to_end((formatter_cls, string))
    return cache[(formatter_cls, string)]


def _number(key, value):
    if key == "tracknumber":
        parts = value.split("/")
        try:
            decimals = len(str(int(parts[1])))
        except (IndexError, ValueError):
            decimals = 2
        try:
            return "%0*d" % (max(2, decimals), int(parts[0]))
        except (TypeError, ValueError):
            return value
    elif key == "discnumber":
        parts = value.split("/")
        try:
            return "%02d" % int(parts[0])
        except (TypeError, ValueError):
            return value
    else:
        return value


class _FileFromPattern(PatternFormatter):
    def _format(self, key, value):
        value = _number(key, value)
        value = value.replace(os.sep, "_")
        value = value.replace("\uff0f", "_")
        return value.strip()

    def _post(self, value, song, keep_extension=True):
        if value:
            assert isinstance(value, str)
            value = fsnative(value)

            if keep_extension:
                fn = song.get("~filename", ".")
                ext = fn[fn.rfind(".") :].lower()
                val_ext = value[-len(ext) :].lower()
                if not ext == val_ext:
                    value += ext.lower()

            if os.name == "nt":
                assert isinstance(value, str)
                value = strip_win32_incompat_from_path(value)

            value = os.path.expanduser(value)
            value = limit_path(value)

            if os.sep in value and not os.path.isabs(value):
                raise ValueError(f"Pattern is not rooted: {value!r}")
            return value
        return fsnative(value)


class _ArbitraryExtensionFileFromPattern(_FileFromPattern):
    """Allows filename-like output with extensions different from the song."""

    def _post(self, value, song, keep_extension=False):
        return super()._post(value, song, keep_extension)


class _XMLFromPattern(PatternFormatter):
    def _format(self, key, value):
        return util.escape(value)


def replace_nt_seps(string):
    """On Windows, users may use backslashes in patterns as path separators.
    Since Windows filenames can't use '<>|' anyway, preserving backslash
    escapes is unnecessary, so we just replace them blindly."""
    return string.replace("\\", r"\\") if os.name == "nt" else string


def FileFromPattern(string):
    """Gives fsnative, not unicode"""

    return Pattern(replace_nt_seps(string), _FileFromPattern)


def ArbitraryExtensionFileFromPattern(string):
    return Pattern(replace_nt_seps(string), _ArbitraryExtensionFileFromPattern)


def XMLFromPattern(string):
    return Pattern(string, _XMLFromPattern)


class _XMLFromMarkupPattern(_XMLFromPattern):
    @classmethod
    def _text(cls, string):
        tags = ["b", "big", "i", "s", "sub", "sup", "small", "tt", "u", "span", "a"]
        pat = "(?:{})".format("|".join(tags))

        def repl_func(match):
            orig, pre, body = match.group(0, 1, 2)
            if len(pre) % 2:
                return orig[1:]
            return rf"{pre}<{body}>"

        string = re.sub(rf"(\\*)\[(/?{pat}\s*)]", repl_func, string)
        return re.sub(r"(\\*)\[((a|span)\s+.*?)]", repl_func, string)


def XMLFromMarkupPattern(string):
    """Like XMLFromPattern but allows using [] instead of \\<\\> for
    pango markup to get rid of all the escaping in the common case.

    To get text like "[b]" escape the first '[' like "\\[b]"
    """

    return Pattern(string, _XMLFromMarkupPattern)


class _URLFromPattern(PatternFormatter):
    def _format(self, key, value):
        return quote_plus(value.encode("utf8"))


def URLFromPattern(string):
    return Pattern(string, _URLFromPattern)
