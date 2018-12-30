# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import re
import sre_parse
import unicodedata

from quodlibet import print_d
from quodlibet.util import re_escape

from .db import get_replacement_mapping


def _fixup_literal(literal, in_seq, mapping):
    u = chr(literal)
    if u in mapping:
        u = u + u"".join(mapping[u])
    need_seq = len(u) > 1
    u = re_escape(u)
    if need_seq and not in_seq:
        u = u"[%s]" % u
    return u


def _fixup_literal_list(literals, mapping):
    u = u"".join(map(chr, literals))

    # longest matches first, we will handle contained ones in the replacement
    # function
    reg = u"(%s)" % u"|".join(
        map(re_escape, sorted(mapping.keys(), key=len, reverse=True)))

    def replace_func(match):
        text = match.group(1)
        all_ = u""
        for c in text:
            all_ += _fixup_literal(ord(c), False, mapping)
        if len(text) > 1:
            multi = u"".join(mapping[text])
            if len(multi) > 1:
                multi = "[%s]" % re_escape(multi)
            else:
                multi = re_escape(multi)
            return "(?:%s|%s)" % (all_, multi)
        return all_

    new = u""
    pos = 0
    for match in re.finditer(reg, u):
        new += re_escape(u[pos:match.start()])
        new += replace_func(match)
        pos = match.end()
    new += re_escape(u[pos:])

    return new


def _fixup_not_literal(literal, mapping):
    u = chr(literal)
    return u"[^%s]" % u"".join(re_escape(u + u"".join(mapping.get(u, []))))


def _fixup_range(start, end, mapping):
    extra = []
    for i in range(start, end + 1):
        u = chr(i)
        if u in mapping:
            extra.append(re_escape(u"".join(mapping[u])))

    start = re_escape(chr(start))
    end = re_escape(chr(end))
    return u"%s%s-%s" % ("".join(extra), start, end)


def _merge_literals(pattern):
    done = []
    current = []

    for op, av in pattern:
        op = str(op).lower()
        if op == "literal":
            current.append(av)
        else:
            if current:
                done.append(("literals", tuple(current)))
                current = []
            done.append((op, av))
    if current:
        done.append(("literals", tuple(current)))

    return done


def _construct_in(pattern, mapping):
    negate = False
    parts = []
    for op, av in _merge_literals(pattern):
        op = str(op).lower()

        if op == "range":
            start, end = av
            parts.append(_fixup_range(start, end, mapping))
        elif op == "literals":
            expanded = []
            for c in av:
                v = _fixup_literal(c, True, mapping)
                if v not in expanded:
                    expanded.append(v)
            parts.extend(expanded)
        elif op == "negate":
            negate = True
        elif op == "category":
            av = str(av).lower()
            cats = {
                "category_word": u"\\w",
                "category_not_word": u"\\W",
                "category_digit": u"\\d",
                "category_not_digit": u"\\D",
                "category_space": u"\\s",
                "category_not_space": u"\\S",
            }
            try:
                parts.append(cats[av])
            except KeyError:
                raise NotImplementedError(av)
        else:
            raise NotImplementedError(op)

    return "[%s%s]" % ("^" if negate else "", u"".join(parts))


def _construct_regexp(pattern, mapping, parent=""):
    """Raises NotImplementedError"""

    parts = []

    for op, av in _merge_literals(pattern):
        op = str(op).lower()

        assert op != "literal"

        if op == "not_literal":
            parts.append(_fixup_not_literal(av, mapping))
        elif op == "literals":
            parts.append(_fixup_literal_list(av, mapping))
        elif op == "category":
            av = str(av).lower()
            cats = {
                "category_word": u"\\w",
                "category_not_word": u"\\W",
                "category_digit": u"\\d",
                "category_not_digit": u"\\D",
                "category_space": u"\\s",
                "category_not_space": u"\\S",
            }
            try:
                parts.append(cats[av])
            except KeyError:
                raise NotImplementedError(av)
        elif op == "any":
            parts.append(u".")
        elif op == "in":
            parts.append(_construct_in(av, mapping))
        elif op == "max_repeat" or op == "min_repeat":
            min_, max_, pad = av
            pad = _construct_regexp(pad, mapping)
            if min_ == 1 and max_ == sre_parse.MAXREPEAT:
                parts.append(u"%s+" % pad)
            elif min_ == 0 and max_ == sre_parse.MAXREPEAT:
                parts.append(u"%s*" % pad)
            elif min_ == 0 and max_ == 1:
                parts.append(u"%s?" % pad)
            else:
                parts.append(u"%s{%d,%d}" % (pad, min_, max_))
            if op == "min_repeat":
                parts[-1] = parts[-1] + u"?"
        elif op == "at":
            av = str(av).lower()
            ats = {
                "at_beginning": u"^",
                "at_end": u"$",
                "at_beginning_string": u"\\A",
                "at_boundary": u"\\b",
                "at_non_boundary": u"\\B",
                "at_end_string": u"\\Z",
            }
            try:
                parts.append(ats[av])
            except KeyError:
                raise NotImplementedError(av)
        elif op == "subpattern":
            # Python 3.6 extended this
            # https://bugs.python.org/issue433028
            if len(av) == 4:
                if av[1:3] == (0, 0):
                    av = [av[0], av[-1]]
                else:
                    raise NotImplementedError(op, av)
            group, pad = av
            pad = _construct_regexp(pad, mapping, parent=op)
            if group is None:
                parts.append(u"(?:%s)" % pad)
            else:
                parts.append(u"(%s)" % pad)
        elif op == "assert":
            direction, pad = av
            pad = _construct_regexp(pad, mapping)
            if direction == 1:
                parts.append(u"(?=%s)" % pad)
            elif direction == -1:
                parts.append(u"(?<=%s)" % pad)
            else:
                raise NotImplementedError(direction)
        elif op == "assert_not":
            direction, pad = av
            pad = _construct_regexp(pad, mapping)
            if direction == 1:
                parts.append(u"(?!%s)" % pad)
            elif direction == -1:
                parts.append(u"(?<!%s)" % pad)
            else:
                raise NotImplementedError(direction)
        elif op == "branch":
            dummy, branches = av
            branches = map(lambda b: _construct_regexp(b, mapping), branches)
            pad = u"|".join(branches)
            if parent != "subpattern":
                parts.append("(?:%s)" % pad)
            else:
                parts.append(pad)
        else:
            raise NotImplementedError(op)

    return u"".join(parts)


def re_replace_literals(text, mapping):
    """Raises NotImplementedError or re.error"""

    assert isinstance(text, str)

    pattern = sre_parse.parse(text)
    return _construct_regexp(pattern, mapping)


def re_add_variants(text):
    """Will replace all occurrences of ascii chars
    by a bracket expression containing the character and all its
    variants with a diacritic mark.

    "föhn" -> "[fḟ]ö[hĥȟḣḥḧḩḫẖ][nñńņňǹṅṇṉṋ]"

    In case the passed in regex is invalid raises re.error.

    Supports all regexp except ones with group references. In
    case something is not supported NotImplementedError gets raised.
    """

    assert isinstance(text, str)

    text = unicodedata.normalize("NFC", text)
    return re_replace_literals(text, get_replacement_mapping())


def compile(pattern, ignore_case=True, dot_all=False, asym=False):
    """
    Args:
        pattern (str): a unicode regex
        ignore_case (bool): if case shouuld be ignored when matching
        dot_all (bool): if "." should match newlines
        asym (bool): if ascii should match similar looking unicode chars
    Returns:
        A callable which will return True if the pattern is contained in
        the passed text.
    Raises:
        ValueError: In case the regex is invalid
    """

    assert isinstance(pattern, str)

    pattern = unicodedata.normalize("NFC", pattern)

    if asym:
        try:
            pattern = re_add_variants(pattern)
        except NotImplementedError:
            # too complex, just skip this step
            print_d("regex not supported: %s" % pattern)
        except re.error as e:
            raise ValueError(e)

    mods = re.MULTILINE | re.UNICODE
    if ignore_case:
        mods |= re.IGNORECASE
    if dot_all:
        mods |= re.DOTALL

    try:
        reg = re.compile(pattern, mods)
    except re.error as e:
        raise ValueError(e)
    normalize = unicodedata.normalize

    def search(text):
        return reg.search(normalize("NFC", text))

    return search
