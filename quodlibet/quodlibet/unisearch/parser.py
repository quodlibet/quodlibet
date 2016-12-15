# -*- coding: utf-8 -*-
# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import re
import sre_parse
import unicodedata

from quodlibet.util import re_escape
from quodlibet.compat import text_type, xrange, unichr

from .db import get_replacement_mapping


def _fixup_literal(literal, in_seq, mapping):
    u = unichr(literal)
    if u in mapping:
        u = u + u"".join(mapping[u])
    need_seq = len(u) > 1
    u = re_escape(u)
    if need_seq and not in_seq:
        u = u"[%s]" % u
    return u


def _fixup_literal_list(literals, mapping):
    u = u"".join(map(unichr, literals))

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
            return "(%s|%s)" % (all_, multi)
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
    u = unichr(literal)
    if u in mapping:
        u = u + u"".join(mapping[u])
    u = re_escape(u)
    return u"[^%s]" % u


def _fixup_range(start, end, mapping):
    extra = []
    for i in xrange(start, end + 1):
        u = unichr(i)
        if u in mapping:
            extra.append(re_escape(u"".join(mapping[u])))
    start = re_escape(unichr(start))
    end = re_escape(unichr(end))
    return u"%s%s-%s" % ("".join(extra), start, end)


def _construct_regexp(pattern, mapping):
    """Raises NotImplementedError"""

    parts = []
    literals = []

    for op, av in pattern:
        op = str(op).lower()

        if literals and op != "literal":
            parts.append(_fixup_literal_list(literals, mapping))
            del literals[:]

        if op == "not_literal":
            parts.append(_fixup_not_literal(av, mapping))
        elif op == "literal":
            literals.append(av)
            continue
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
        elif op == "negate":
            parts.append(u"^")
        elif op == "in":
            in_parts = []
            for entry in av:
                op, eav = entry
                op = str(op).lower()
                if op == "literal":
                    in_parts.append(_fixup_literal(eav, True, mapping))
                else:
                    in_parts.append(_construct_regexp([entry], mapping))
            parts.append(u"[%s]" % (u"".join(in_parts)))
        elif op == "range":
            start, end = av
            parts.append(_fixup_range(start, end, mapping))
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
            group, pad = av
            pad = _construct_regexp(pad, mapping)
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
            parts.append(u"%s" % (u"|".join(branches)))
        else:
            raise NotImplementedError(op)

    if literals:
        parts.append(_fixup_literal_list(literals, mapping))
        del literals[:]

    return u"".join(parts)


def re_replace_literals(text, mapping):
    """Raises NotImplementedError or re.error"""

    assert isinstance(text, text_type)

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

    assert isinstance(text, text_type)

    text = unicodedata.normalize("NFC", text)
    return re_replace_literals(text, get_replacement_mapping())
