# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from collections.abc import Callable
import re
import unicodedata

try:
    from re import _parser as sre_parse  # type: ignore
    from re import _constants as sre_constants  # type: ignore
except ImportError:
    import sre_parse
    import sre_constants

from quodlibet import print_d
from quodlibet.util import re_escape

from .db import get_replacement_mapping


def _fixup_literal(literal, in_seq, mapping):
    u = chr(literal)
    if u in mapping:
        u = u + "".join(mapping[u])
    need_seq = len(u) > 1
    u = re_escape(u)
    if need_seq and not in_seq:
        u = f"[{u}]"
    return u


def _fixup_literal_list(literals, mapping):
    u = "".join(map(chr, literals))

    # longest matches first, we will handle contained ones in the replacement
    # function
    reg = "({})".format(
        "|".join(map(re_escape, sorted(mapping.keys(), key=len, reverse=True)))
    )

    def replace_func(match):
        text = match.group(1)
        all_ = ""
        for c in text:
            all_ += _fixup_literal(ord(c), False, mapping)
        if len(text) > 1:
            multi = "".join(mapping[text])
            if len(multi) > 1:
                multi = f"[{re_escape(multi)}]"
            else:
                multi = re_escape(multi)
            return f"(?:{all_}|{multi})"
        return all_

    new = ""
    pos = 0
    for match in re.finditer(reg, u):
        new += re_escape(u[pos : match.start()])
        new += replace_func(match)
        pos = match.end()
    new += re_escape(u[pos:])

    return new


def _fixup_not_literal(literal, mapping):
    u = chr(literal)
    return "[^{}]".format("".join(re_escape(u + "".join(mapping.get(u, [])))))


def _fixup_range(start, end, mapping):
    extra = []
    for i in range(start, end + 1):
        u = chr(i)
        if u in mapping:
            extra.append(re_escape("".join(mapping[u])))

    start = re_escape(chr(start))
    end = re_escape(chr(end))
    return "{}{}-{}".format("".join(extra), start, end)


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
                "category_word": "\\w",
                "category_not_word": "\\W",
                "category_digit": "\\d",
                "category_not_digit": "\\D",
                "category_space": "\\s",
                "category_not_space": "\\S",
            }
            try:
                parts.append(cats[av])
            except KeyError as e:
                raise NotImplementedError(av) from e
        else:
            raise NotImplementedError(op)

    return "[{}{}]".format("^" if negate else "", "".join(parts))


def _construct_regexp(
    pattern: sre_parse.SubPattern, mapping: dict[str, list[str]], parent=""
) -> str:
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
                "category_word": "\\w",
                "category_not_word": "\\W",
                "category_digit": "\\d",
                "category_not_digit": "\\D",
                "category_space": "\\s",
                "category_not_space": "\\S",
            }
            try:
                parts.append(cats[av])
            except KeyError as e:
                raise NotImplementedError(av) from e
        elif op == "any":
            parts.append(".")
        elif op == "in":
            parts.append(_construct_in(av, mapping))
        elif op == "max_repeat" or op == "min_repeat":
            min_, max_, pad = av
            pad = _construct_regexp(pad, mapping)
            if min_ == 1 and max_ == sre_constants.MAXREPEAT:
                parts.append(f"{pad}+")
            elif min_ == 0 and max_ == sre_constants.MAXREPEAT:
                parts.append(f"{pad}*")
            elif min_ == 0 and max_ == 1:
                parts.append(f"{pad}?")
            else:
                parts.append("%s{%d,%d}" % (pad, min_, max_))
            if op == "min_repeat":
                parts[-1] = parts[-1] + "?"
        elif op == "at":
            av = str(av).lower()
            ats = {
                "at_beginning": "^",
                "at_end": "$",
                "at_beginning_string": "\\A",
                "at_boundary": "\\b",
                "at_non_boundary": "\\B",
                "at_end_string": "\\Z",
            }
            try:
                parts.append(ats[av])
            except KeyError as e:
                raise NotImplementedError(av) from e
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
                parts.append(f"(?:{pad})")
            else:
                parts.append(f"({pad})")
        elif op == "assert":
            direction, pad = av
            pad = _construct_regexp(pad, mapping)
            if direction == 1:
                parts.append(f"(?={pad})")
            elif direction == -1:
                parts.append(f"(?<={pad})")
            else:
                raise NotImplementedError(direction)
        elif op == "assert_not":
            direction, pad = av
            pad = _construct_regexp(pad, mapping)
            if direction == 1:
                parts.append(f"(?!{pad})")
            elif direction == -1:
                parts.append(f"(?<!{pad})")
            else:
                raise NotImplementedError(direction)
        elif op == "branch":
            dummy, branches = av
            branches = (_construct_regexp(b, mapping) for b in branches)
            pad = "|".join(branches)
            if parent != "subpattern":
                parts.append(f"(?:{pad})")
            else:
                parts.append(pad)
        else:
            raise NotImplementedError(op)

    return "".join(parts)


def re_replace_literals(text: str, mapping: dict[str, list[str]]) -> str:
    """Raises NotImplementedError or re.error"""

    assert isinstance(text, str)

    pattern = sre_parse.parse(text)
    return _construct_regexp(pattern, mapping)


def re_add_variants(text: str) -> str:
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


def compile(
    pattern: str, ignore_case: bool = True, dot_all: bool = False, asym: bool = False
) -> Callable[[str], bool]:
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
            print_d(f"regex not supported: {pattern}")
        except re.error as e:
            raise ValueError(e) from e

    mods = re.MULTILINE | re.UNICODE
    if ignore_case:
        mods |= re.IGNORECASE
    if dot_all:
        mods |= re.DOTALL

    try:
        reg = re.compile(pattern, mods)
    except re.error as e:
        raise ValueError(e) from e
    normalize = unicodedata.normalize

    def search(text: str):
        return bool(reg.search(normalize("NFC", text)))

    return search
