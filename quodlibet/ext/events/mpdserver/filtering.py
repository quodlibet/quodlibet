# Copyright 2026 Felicián Németh <felician.nemeth@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Translate MPD filter expressions into Quod Libet query syntax."""

from __future__ import annotations

from datetime import datetime, timezone
import time

from quodlibet.util import parse_date, re_escape


class MPDFilterError(Exception):
    pass


class MPDSearchConverter:
    TAG_MAP = {
        "file": "~filename",
        "title": "title",
        "titlesort": "titlesort",
        "album": "album",
        "albumsort": "albumsort",
        "artist": "artist",
        "artistsort": "artistsort",
        "albumartist": "albumartist,artist",
        "albumartistsort": "albumartistsort",
        "track": "tracknumber",
        "name": "name",
        "genre": "genre",
        "mood": "mood",
        "date": "date,~year",
        "originaldate": "originaldate,~originalyear",
        "composer": "composer",
        "composersort": "composersort",
        "performer": "performer",
        "conductor": "conductor",
        "work": "work",
        "ensemble": "ensemble",
        "movement": "movement",
        "movementnumber": "movementnumber",
        "showmovement": "showmovement",
        "location": "location",
        "grouping": "grouping",
        "comment": "comment",
        "disc": "discnumber",
        "label": "label",
        "musicbrainz_artistid": "musicbrainz_artistid",
        "musicbrainz_albumid": "musicbrainz_albumid",
        "musicbrainz_albumartistid": "musicbrainz_albumartistid",
        "musicbrainz_trackid": "musicbrainz_trackid",
        "musicbrainz_releasegroupid": "musicbrainz_releasegroupid",
        "musicbrainz_releasetrackid": "musicbrainz_releasetrackid",
        "musicbrainz_workid": "musicbrainz_workid",
        "any": "any",
    }
    ANY_TAGS = (
        "title",
        "artist",
        "album",
        "albumartist",
        "genre",
        "~filename",
    )
    CASE_FALLBACK = {
        "eq_cs": "==",
        "eq_ci": "==",
        "!eq_cs": "!=",
        "!eq_ci": "!=",
        "contains_cs": "contains",
        "contains_ci": "contains",
        "!contains_cs": "!contains",
        "!contains_ci": "!contains",
        "starts_with_cs": "starts_with",
        "starts_with_ci": "starts_with",
        "!starts_with_cs": "!starts_with",
        "!starts_with_ci": "!starts_with",
    }

    def to_query(self, filter_expr: str) -> str:
        expr = filter_expr.strip()
        if not expr:
            raise MPDFilterError("Wrong arg count")

        tokens = _tokenize(expr)
        parser = _FilterParser(tokens)
        node = parser.parse_filter()
        if not parser.is_done():
            raise MPDFilterError("invalid arg")
        return node.to_query(self)

    def legacy_to_query(self, args: list[str]) -> str:
        if not args:
            raise MPDFilterError("Wrong arg count")
        if len(args) % 2:
            raise MPDFilterError("Wrong arg count")

        terms = []
        # Legacy MPD form: search <tag> <value> [<tag> <value> ...]
        # We treat it as a case-insensitive substring search.
        for index in range(0, len(args), 2):
            tag = args[index].lower()
            value = args[index + 1]
            terms.append(self._term_query(tag, "contains", value))
        return _combine_query("&", terms)

    def _term_query(self, tag: str, op: str, value: str) -> str:
        if tag not in self.TAG_MAP:
            raise MPDFilterError("invalid arg")

        qtag = self.TAG_MAP[tag]

        # TODO: Respect case-sensitive operators when mapping to queries.
        normalized = self.CASE_FALLBACK.get(op, op)
        negate = False

        if normalized in {"!=", "!contains", "!starts_with", "!~"}:
            negate = True
            normalized = normalized[1:]
            if normalized == "=":
                normalized = "=="

        if normalized == "==":
            term = self._format_match(qtag, value, exact=True)
        elif normalized == "contains":
            term = self._format_contains(qtag, value)
        elif normalized == "starts_with":
            term = self._format_starts_with(qtag, value)
        elif normalized == "=~":
            # MPD uses PCRE if available; Quod Libet uses Python regex. We fall
            # back to Python regex search semantics here.
            term = self._format_regex(qtag, value)
        else:
            raise MPDFilterError("invalid arg")

        if negate:
            return _negate_query(term)
        return term

    def _any_query(self, value: str, exact: bool) -> str:
        terms = [_format_query_term(tag, value, exact) for tag in self.ANY_TAGS]
        return _combine_query("|", terms)

    def _format_match(
        self,
        tag: str,
        value: str,
        exact: bool = False,
        prefix: bool = False,
    ) -> str:
        if "," in tag:
            terms = [
                self._format_match(part.strip(), value, exact, prefix)
                for part in tag.split(",")
            ]
            return _combine_query("|", terms)
        if tag == "any":
            if prefix:
                terms = [
                    _format_regex_term(t, _format_prefix_regex(value))
                    for t in self.ANY_TAGS
                ]
                return _combine_query("|", terms)
            return self._any_query(value, exact)

        if prefix:
            return _format_regex_term(tag, _format_prefix_regex(value))

        return _format_query_term(tag, value, exact)

    def _format_contains(self, tag: str, value: str) -> str:
        return self._format_regex_query(tag, re_escape(value))

    def _format_starts_with(self, tag: str, value: str) -> str:
        return self._format_regex_query(tag, _format_prefix_regex(value))

    def _format_regex_query(self, tag: str, pattern: str) -> str:
        if "," in tag:
            tags = tag.split(",")
            terms = [_format_regex_term(part.strip(), pattern) for part in tags]
            return _combine_query("|", terms)
        if tag == "any":
            terms = [_format_regex_term(t, pattern) for t in self.ANY_TAGS]
            return _combine_query("|", terms)
        return _format_regex_term(tag, pattern)

    def _format_regex(self, tag: str, value: str) -> str:
        pattern = value.replace("/", "\\/")
        if "," in tag:
            terms = [
                _format_regex_term(part.strip(), pattern) for part in tag.split(",")
            ]
            return _combine_query("|", terms)
        if tag == "any":
            terms = [_format_regex_term(t, pattern) for t in self.ANY_TAGS]
            return _combine_query("|", terms)
        return _format_regex_term(tag, pattern)


def _format_query_term(tag: str, value: str, exact: bool) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    if exact:
        return f'{tag}="{escaped}"'
    return f"{tag}={escaped}"


def _format_regex_term(tag: str, pattern: str) -> str:
    return f"{tag}=/{pattern}/d"


def _format_prefix_regex(value: str) -> str:
    return f"^{re_escape(value)}"


def _negate_query(query: str) -> str:
    return f"!{query}"


def _negate_term(tag: str, term: str) -> str:
    if tag == "any" or "," in tag:
        return _negate_query(term)
    if term.startswith(f"{tag}="):
        return term.replace("=", "!=", 1)
    return _negate_query(term)


def _combine_query(op: str, terms: list[str]) -> str:
    if len(terms) == 1:
        return terms[0]
    return f"{op}({', '.join(terms)})"


class _FilterNode:
    def to_query(self, converter: MPDSearchConverter) -> str:
        raise NotImplementedError


class _TermNode(_FilterNode):
    def __init__(self, tag: str, op: str, value: str) -> None:
        self.tag = tag
        self.op = op
        self.value = value

    def to_query(self, converter: MPDSearchConverter) -> str:
        return converter._term_query(self.tag, self.op, self.value)


class _BaseNode(_FilterNode):
    def __init__(self, value: str) -> None:
        self.value = value

    def to_query(self, converter: MPDSearchConverter) -> str:
        # MPD base matches a subdirectory. We approximate this as a filename
        # substring search because Quod Libet has no music-dir-relative view.
        return converter._term_query("file", "contains", self.value)


class _SinceNode(_FilterNode):
    def __init__(self, tag: str, value: str) -> None:
        self.tag = tag
        self.value = value

    def to_query(self, converter: MPDSearchConverter) -> str:
        timestamp = _parse_timestamp(self.value)
        age = max(0, int(time.time()) - timestamp)
        return f"#({self.tag} <= {age:d})"


class _AudioFormatNode(_FilterNode):
    def __init__(self, op: str, value: str) -> None:
        self.op = op
        self.value = value

    def to_query(self, converter: MPDSearchConverter) -> str:
        return _audioformat_query(self.op, self.value)


class _PrioNode(_FilterNode):
    def __init__(self, op: str, value: str) -> None:
        self.op = op
        self.value = value

    def to_query(self, converter: MPDSearchConverter) -> str:
        number = _parse_int(self.value)
        return f"#(prio {self.op} {number:d})"


class _AndNode(_FilterNode):
    def __init__(self, left: _FilterNode, right: _FilterNode) -> None:
        self.left = left
        self.right = right

    def to_query(self, converter: MPDSearchConverter) -> str:
        return _combine_query(
            "&",
            [self.left.to_query(converter), self.right.to_query(converter)],
        )


class _OrNode(_FilterNode):
    def __init__(self, left: _FilterNode, right: _FilterNode) -> None:
        self.left = left
        self.right = right

    def to_query(self, converter: MPDSearchConverter) -> str:
        return _combine_query(
            "|",
            [self.left.to_query(converter), self.right.to_query(converter)],
        )


class _NotNode(_FilterNode):
    def __init__(self, node: _FilterNode) -> None:
        self.node = node

    def to_query(self, converter: MPDSearchConverter) -> str:
        return _negate_query(self.node.to_query(converter))


class _Token:
    def __init__(self, value: str, kind: str) -> None:
        self.value = value
        self.kind = kind


class _FilterParser:
    def __init__(self, tokens: list[_Token]) -> None:
        self._tokens = tokens
        self._index = 0

    def is_done(self) -> bool:
        return self._index >= len(self._tokens)

    def parse_filter(self) -> _FilterNode:
        return self._parse_group()

    def _parse_group(self) -> _FilterNode:
        self._expect("(")
        node = self._parse_or()
        self._expect(")")
        return node

    def _parse_or(self) -> _FilterNode:
        node = self._parse_and()
        while True:
            token = self._peek()
            if token is None:
                break
            if token.value == "|" or token.value.upper() == "OR":
                self._next()
                node = _OrNode(node, self._parse_and())
                continue
            break
        return node

    def _parse_and(self) -> _FilterNode:
        node = self._parse_term()
        while True:
            token = self._peek()
            if token is None:
                break
            if token.value.upper() != "AND":
                break
            self._next()
            node = _AndNode(node, self._parse_term())
        return node

    def _parse_term(self) -> _FilterNode:
        token = self._peek()
        if token is None:
            raise MPDFilterError("invalid arg")
        if token.value == "!":
            self._next()
            return _NotNode(self._parse_group())
        if token.value == "(":
            return self._parse_group()
        return self._parse_predicate()

    def _parse_predicate(self) -> _FilterNode:
        tag = self._expect_word().lower()

        if tag == "base":
            value = self._expect_value()
            return _BaseNode(value)

        if tag in {"added-since", "modified-since"}:
            value = self._expect_value()
            mapped = "added" if tag == "added-since" else "mtime"
            return _SinceNode(mapped, value)

        if tag == "audioformat":
            op = self._expect_operator({"==", "=~"})
            value = self._expect_value()
            return _AudioFormatNode(op, value)

        if tag == "prio":
            op = self._expect_operator({"==", "!=", ">=", "<=", ">", "<"})
            value = self._expect_value()
            return _PrioNode(op, value)

        op = self._expect_operator(
            {
                "==",
                "!=",
                "contains",
                "!contains",
                "starts_with",
                "!starts_with",
                "=~",
                "!~",
                "eq_cs",
                "eq_ci",
                "!eq_cs",
                "!eq_ci",
                "contains_cs",
                "contains_ci",
                "!contains_cs",
                "!contains_ci",
                "starts_with_cs",
                "starts_with_ci",
                "!starts_with_cs",
                "!starts_with_ci",
            }
        )
        value = self._expect_value()
        return _TermNode(tag, op, value)

    def _peek(self) -> _Token | None:
        if self._index >= len(self._tokens):
            return None
        return self._tokens[self._index]

    def _next(self) -> _Token | None:
        if self._index >= len(self._tokens):
            return None
        value = self._tokens[self._index]
        self._index += 1
        return value

    def _expect(self, value: str) -> None:
        token = self._next()
        if token is None or token.value != value:
            raise MPDFilterError("invalid arg")

    def _expect_word(self) -> str:
        token = self._next()
        if token is None or token.kind != "word":
            raise MPDFilterError("invalid arg")
        return token.value

    def _expect_value(self) -> str:
        token = self._next()
        if token is None or token.kind not in {"word", "string"}:
            raise MPDFilterError("invalid arg")
        return token.value

    def _expect_operator(self, allowed: set[str]) -> str:
        token = self._next()
        if token is None or token.kind not in {"word", "op"}:
            raise MPDFilterError("invalid arg")
        op = token.value.lower()
        if op not in allowed:
            raise MPDFilterError("invalid arg")
        return op


def _tokenize(expr: str) -> list[_Token]:
    tokens: list[_Token] = []
    i = 0
    while i < len(expr):
        char = expr[i]
        if char.isspace():
            i += 1
            continue
        if char in "()|":
            tokens.append(_Token(char, "symbol"))
            i += 1
            continue
        if char in ('"', "'"):
            quote = char
            i += 1
            buf = []
            while i < len(expr):
                if expr[i] == "\\" and i + 1 < len(expr):
                    buf.append(expr[i + 1])
                    i += 2
                    continue
                if expr[i] == quote:
                    i += 1
                    break
                buf.append(expr[i])
                i += 1
            else:
                raise MPDFilterError("invalid arg")
            tokens.append(_Token("".join(buf), "string"))
            continue
        if char == "!" and i + 1 < len(expr) and expr[i + 1].isalpha():
            start = i
            i += 1
            while i < len(expr) and not expr[i].isspace() and expr[i] not in "()|=!<>":
                i += 1
            tokens.append(_Token(expr[start:i], "word"))
            continue
        if char in "=!<>":
            if expr.startswith("==", i):
                tokens.append(_Token("==", "op"))
                i += 2
                continue
            if expr.startswith("!=", i):
                tokens.append(_Token("!=", "op"))
                i += 2
                continue
            if expr.startswith("=~", i):
                tokens.append(_Token("=~", "op"))
                i += 2
                continue
            if expr.startswith("!~", i):
                tokens.append(_Token("!~", "op"))
                i += 2
                continue
            if expr.startswith(">=", i):
                tokens.append(_Token(">=", "op"))
                i += 2
                continue
            if expr.startswith("<=", i):
                tokens.append(_Token("<=", "op"))
                i += 2
                continue
            if char in "<>":
                tokens.append(_Token(char, "op"))
                i += 1
                continue
            if char == "!":
                tokens.append(_Token("!", "symbol"))
                i += 1
                continue
            raise MPDFilterError("invalid arg")

        start = i
        while i < len(expr):
            if expr[i].isspace() or expr[i] in "()|=!<>":
                break
            i += 1
        tokens.append(_Token(expr[start:i], "word"))

    return tokens


def _parse_int(value: str) -> int:
    try:
        return int(value)
    except ValueError as e:
        raise MPDFilterError("invalid arg") from e


def _parse_timestamp(value: str) -> int:
    if value.isdigit():
        return _parse_int(value)

    iso_value = value
    if iso_value.endswith("Z"):
        iso_value = iso_value[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(iso_value)
    except ValueError:
        try:
            return int(parse_date(value))
        except ValueError as e:
            raise MPDFilterError("invalid arg") from e

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp())


def _audioformat_query(op: str, value: str) -> str:
    parts = value.split(":")
    if len(parts) != 3:
        raise MPDFilterError("invalid arg")
    samplerate, bitdepth, channels = parts

    allow_wildcard = op == "=~"

    terms = []
    terms.extend(_audioformat_term("samplerate", samplerate, allow_wildcard))
    terms.extend(_audioformat_term("bitdepth", bitdepth, allow_wildcard))
    terms.extend(_audioformat_term("channels", channels, allow_wildcard))

    if not terms:
        raise MPDFilterError("invalid arg")
    return _combine_query("&", terms)


def _audioformat_term(tag: str, value: str, allow_wildcard: bool) -> list[str]:
    if value == "*":
        if allow_wildcard:
            return []
        raise MPDFilterError("invalid arg")

    number = _parse_int(value)
    return [f"#({tag} == {number:d})"]
