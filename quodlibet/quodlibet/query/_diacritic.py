# -*- coding: utf-8 -*-
# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

# A simple top-down parser for the query grammar. It's basically textbook,
# but it could use some cleaning up. It builds the requisite match.*
# objects as it goes, which is where the interesting stuff will happen.

"""
Ways to let ASCII characters match other unicode characters which
can be decomposed into one ASCII character and one or more combining
diacritic marks. This allows to match e.g. "Múm" using "Mum".

re_add_variants(u"Mum") =>
    u"[MḾṀṂ][uùúûüũūŭůűųưǔǖǘǚǜȕȗṳṵṷṹṻụủứừửữự][mḿṁṃ]"

This is also called Asymmetric Search:
    http://unicode.org/reports/tr10/#Asymmetric_Search

TODO: support replacing multiple characters, so AE matches Æ
"""

import re
import sre_parse
import unicodedata
import sys

from quodlibet.util import re_escape
from quodlibet.compat import iteritems


_DIACRITIC_CACHE = {
    u'\u0300': (u'AEINOUWYaeinouwy\u0391\u0395\u0397\u0399\u039f\u03a5\u03a9'
                u'\u03b1\u03b5\u03b7\u03b9\u03bf\u03c5\u03c9\u0415\u0418'
                u'\u0435\u0438'),
    u'\u0300\u0345': u'\u03b1\u03b7\u03c9',
    u'\u0301': (u'ACEGIKLMNOPRSUWYZacegiklmnoprsuwyz\xc6\xd8\xe6\xf8\u0391'
                u'\u0395\u0397\u0399\u039f\u03a5\u03a9\u03b1\u03b5\u03b7'
                u'\u03b9\u03bf\u03c5\u03c9\u0413\u041a\u0433\u043a'),
    u'\u0301\u0307': u'Ss',
    u'\u0301\u0345': u'\u03b1\u03b7\u03c9',
    u'\u0302': u'ACEGHIJOSUWYZaceghijosuwyz',
    u'\u0302\u0300': u'AEOaeo',
    u'\u0302\u0301': u'AEOaeo',
    u'\u0302\u0303': u'AEOaeo',
    u'\u0302\u0309': u'AEOaeo',
    u'\u0303': u'AEINOUVYaeinouvy',
    u'\u0303\u0301': u'OUou',
    u'\u0303\u0304': u'Oo',
    u'\u0303\u0308': u'Oo',
    u'\u0304': (u'AEGIOUYaegiouy\xc6\xe6\u0391\u0399\u03a5\u03b1\u03b9'
                u'\u03c5\u0418\u0423\u0438\u0443'),
    u'\u0304\u0300': u'EOeo',
    u'\u0304\u0301': u'EOeo',
    u'\u0304\u0308': u'Uu',
    u'\u0306': (u'AEGIOUaegiou\u0391\u0399\u03a5\u03b1\u03b9\u03c5\u0410'
                u'\u0415\u0416\u0418\u0423\u0430\u0435\u0436\u0438\u0443'),
    u'\u0306\u0300': u'Aa',
    u'\u0306\u0301': u'Aa',
    u'\u0306\u0303': u'Aa',
    u'\u0306\u0309': u'Aa',
    u'\u0307': u'ABCDEFGHIMNOPRSTWXYZabcdefghmnoprstwxyz',
    u'\u0307\u0304': u'AOao',
    u'\u0308': (u'AEHIOUWXYaehiotuwxy\u0399\u03a5\u03b9\u03c5\u0406\u0410'
                u'\u0415\u0416\u0417\u0418\u041e\u0423\u0427\u042b\u042d'
                u'\u0430\u0435\u0436\u0437\u0438\u043e\u0443\u0447\u044b'
                u'\u044d\u0456\u04d8\u04d9\u04e8\u04e9'),
    u'\u0308\u0300': u'Uu\u03b9\u03c5',
    u'\u0308\u0301': u'IUiu\u03b9\u03c5',
    u'\u0308\u0304': u'AOUaou',
    u'\u0308\u030c': u'Uu',
    u'\u0308\u0342': u'\u03b9\u03c5',
    u'\u0309': u'AEIOUYaeiouy',
    u'\u030a': u'AUauwy',
    u'\u030a\u0301': u'Aa',
    u'\u030b': u'OUou\u0423\u0443',
    u'\u030c': u'ACDEGHIKLNORSTUZacdeghijklnorstuz\u01b7\u0292',
    u'\u030c\u0307': u'Ss',
    u'\u030f': u'AEIORUaeioru\u0474\u0475',
    u'\u0311': u'AEIORUaeioru',
    u'\u0313': (u'\u0391\u0395\u0397\u0399\u039f\u03a9\u03b1\u03b5\u03b7'
                u'\u03b9\u03bf\u03c1\u03c5\u03c9'),
    u'\u0313\u0300': (u'\u0391\u0395\u0397\u0399\u039f\u03a9\u03b1\u03b5'
                      u'\u03b7\u03b9\u03bf\u03c5\u03c9'),
    u'\u0313\u0300\u0345': u'\u0391\u0397\u03a9\u03b1\u03b7\u03c9',
    u'\u0313\u0301': (u'\u0391\u0395\u0397\u0399\u039f\u03a9\u03b1\u03b5'
                      u'\u03b7\u03b9\u03bf\u03c5\u03c9'),
    u'\u0313\u0301\u0345': u'\u0391\u0397\u03a9\u03b1\u03b7\u03c9',
    u'\u0313\u0342': u'\u0391\u0397\u0399\u03a9\u03b1\u03b7\u03b9\u03c5\u03c9',
    u'\u0313\u0342\u0345': u'\u0391\u0397\u03a9\u03b1\u03b7\u03c9',
    u'\u0313\u0345': u'\u0391\u0397\u03a9\u03b1\u03b7\u03c9',
    u'\u0314': (u'\u0391\u0395\u0397\u0399\u039f\u03a1\u03a5\u03a9\u03b1'
                u'\u03b5\u03b7\u03b9\u03bf\u03c1\u03c5\u03c9'),
    u'\u0314\u0300': (u'\u0391\u0395\u0397\u0399\u039f\u03a5\u03a9\u03b1'
                      u'\u03b5\u03b7\u03b9\u03bf\u03c5\u03c9'),
    u'\u0314\u0300\u0345': u'\u0391\u0397\u03a9\u03b1\u03b7\u03c9',
    u'\u0314\u0301': (u'\u0391\u0395\u0397\u0399\u039f\u03a5\u03a9\u03b1'
                      u'\u03b5\u03b7\u03b9\u03bf\u03c5\u03c9'),
    u'\u0314\u0301\u0345': u'\u0391\u0397\u03a9\u03b1\u03b7\u03c9',
    u'\u0314\u0342': (u'\u0391\u0397\u0399\u03a5\u03a9\u03b1\u03b7\u03b9'
                      u'\u03c5\u03c9'),
    u'\u0314\u0342\u0345': u'\u0391\u0397\u03a9\u03b1\u03b7\u03c9',
    u'\u0314\u0345': u'\u0391\u0397\u03a9\u03b1\u03b7\u03c9',
    u'\u031b': u'OUou',
    u'\u031b\u0300': u'OUou',
    u'\u031b\u0301': u'OUou',
    u'\u031b\u0303': u'OUou',
    u'\u031b\u0309': u'OUou',
    u'\u031b\u0323': u'OUou',
    u'\u0323': u'ABDEHIKLMNORSTUVWYZabdehiklmnorstuvwyz',
    u'\u0323\u0302': u'AEOaeo',
    u'\u0323\u0304': u'LRlr',
    u'\u0323\u0306': u'Aa',
    u'\u0323\u0307': u'Ss',
    u'\u0324': u'Uu',
    u'\u0325': u'Aa',
    u'\u0326': u'STst',
    u'\u0327': u'CDEGHKLNRSTcdeghklnrst',
    u'\u0327\u0301': u'Cc',
    u'\u0327\u0306': u'Ee',
    u'\u0328': u'AEIOUaeiou',
    u'\u0328\u0304': u'Oo',
    u'\u032d': u'DELNTUdelntu',
    u'\u032e': u'Hh',
    u'\u0330': u'EIUeiu',
    u'\u0331': u'BDKLNRTZbdhklnrtz',
    u'\u0342': u'\u03b1\u03b7\u03b9\u03c5\u03c9',
    u'\u0342\u0345': u'\u03b1\u03b7\u03c9',
    u'\u0345': u'\u0391\u0397\u03a9\u03b1\u03b7\u03c9'
}

# See misc/uca_decomps.py
_UCA_DECOMPS = {
    u'AA': u'\ua732',
    u'AE': u'\xc6\u01e2\u01fc',
    u'AO': u'\ua734',
    u'AU': u'\ua736',
    u'AV': u'\ua738\ua73a',
    u'AY': u'\ua73c',
    u'D': u'\xd0\u0110\ua779',
    u'DZ': u'\u01c4\u01f1',
    u'Dz': u'\u01c5\u01f2',
    u'F': u'\ua77b',
    u'G': u'\ua77d',
    u'H': u'\u0126',
    u'IJ': u'\u0132',
    u'L': u'\u0141',
    u'LJ': u'\u01c7',
    u'LL': u'\u1efa',
    u'Lj': u'\u01c8',
    u'NJ': u'\u01ca',
    u'Nj': u'\u01cb',
    u'O': u'\xd8\u01fe',
    u'OE': u'\u0152',
    u'OO': u'\ua74e',
    u'R': u'\ua782',
    u'S': u'\ua784',
    u'SS': u'\u1e9e',
    u'T': u'\ua786',
    u'Tz': u'\ua728',
    u'VY': u'\ua760',
    u'aa': u'\ua733',
    u'ae': u'\xe6\u01e3\u01fd',
    u'ao': u'\ua735',
    u'au': u'\ua737',
    u'av': u'\ua739\ua73b',
    u'ay': u'\ua73d',
    u'd': u'\xf0\u0111\ua77a',
    u'db': u'\u0238',
    u'dz': u'\u01c6\u01f3\u02a3',
    u'd\u0291': u'\u02a5',
    u'd\u0292': u'\u02a4',
    u'f': u'\ua77c',
    u'ff': u'\ufb00',
    u'ffi': u'\ufb03',
    u'ffl': u'\ufb04',
    u'fi': u'\ufb01',
    u'fl': u'\ufb02',
    u'f\u014b': u'\u02a9',
    u'g': u'\u1d79',
    u'h': u'\u0127\u210f',
    u'ij': u'\u0133',
    u'l': u'\u0142',
    u'lj': u'\u01c9',
    u'll': u'\u1efb',
    u'ls': u'\u02aa',
    u'lz': u'\u02ab',
    u'n': u'\u0149',
    u'nj': u'\u01cc',
    u'o': u'\xf8\u01ff',
    u'oe': u'\u0153',
    u'oo': u'\ua74f',
    u'qp': u'\u0239',
    u'r': u'\ua783',
    u's': u'\ua785',
    u'ss': u'\xdf',
    u'st': u'\ufb05\ufb06',
    u't': u'\ua787',
    u'th': u'\u1d7a',
    u'ts': u'\u01be\u02a6',
    u'tz': u'\ua729',
    u't\u0255': u'\u02a8',
    u't\u0283': u'\u02a7',
    u'vy': u'\ua761',
    u'zw': u'\u018d',
    u'\u039a\u03b1\u03b9': u'\u03cf',
    u'\u03ba\u03b1\u03b9': u'\u03d7',
    u'\u03c3': u'\u03c2\u03f2\U0001d6d3\U0001d70d'
               u'\U0001d747\U0001d781\U0001d7bb',
    u'\u0413': u'\u0490',
    u'\u041e': u'\ua668\ua66a\ua66c',
    u'\u0433': u'\u0491',
    u'\u043e': u'\ua669\ua66b\ua66d',
    u'\u0565\u0582': u'\u0587',
    u'\u0574\u0565': u'\ufb14',
    u'\u0574\u056b': u'\ufb15',
    u'\u0574\u056d': u'\ufb17',
    u'\u0574\u0576': u'\ufb13',
    u'\u057e\u0576': u'\ufb16',
    u'\u2c95\u2c81\u2c93': u'\u2ce4',
}


def diacritic_for_letters(regenerate=False):
    """Returns a mapping for combining diacritic mark to ascii characters
    for which they can be used to combine to a single unicode char.

    (actually not ascii, but unicode from the Lu/Ll/Lt categories,
    but mainly ascii)

    Since this is quite expensive to compute, the result is a cached version
    unless regenerate != True. regenerate = True is used for unittests
    to validate the cache.
    """

    if not regenerate:
        return _DIACRITIC_CACHE

    d = {}
    for i in xrange(sys.maxunicode):
        u = unichr(i)
        n = unicodedata.normalize("NFKD", u)
        if len(n) <= 1:
            continue
        if unicodedata.category(u) not in ("Lu", "Ll", "Lt"):
            continue
        if not all(map(unicodedata.combining, n[1:])):
            continue
        d.setdefault(n[1:], set()).add(n[0])

    for k, v in d.items():
        d[k] = u"".join(sorted(v))

    return d


def generate_re_mapping(_diacritic_for_letters):
    letter_to_variants = {}

    # combine combining characters with the ascii chars
    for dia, letters in iteritems(_diacritic_for_letters):
        for c in letters:
            unichar = unicodedata.normalize("NFKC", c + dia)
            letter_to_variants.setdefault(c, []).append(unichar)

    # create strings to replace ascii with
    for k, v in letter_to_variants.items():
        letter_to_variants[k] = u"".join(sorted(v))

    return letter_to_variants


def _fixup_literal(literal, in_seq, mapping):
    u = unichr(literal)
    if u in mapping:
        u = u + mapping[u]
    need_seq = len(u) > 1
    u = re_escape(u)
    if need_seq and not in_seq:
        u = u"[%s]" % u
    return u


def _fixup_literal_list(literals, mapping):
    u = re_escape("".join(map(unichr, literals)))

    if not mapping:
        return u

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
            multi = mapping[text]
            if len(multi) > 1:
                multi = "[%s]" % re_escape(multi)
            else:
                multi = re_escape(multi)
            return "(%s|%s)" % (all_, multi)
        return all_

    return re.sub(reg, replace_func, u)


def _fixup_not_literal(literal, mapping):
    u = unichr(literal)
    if u in mapping:
        u = u + mapping[u]
    u = re_escape(u)
    return u"[^%s]" % u


def _fixup_range(start, end, mapping):
    extra = []
    for i in xrange(start, end + 1):
        u = unichr(i)
        if u in mapping:
            extra.append(re_escape(mapping[u]))
    start = re_escape(unichr(start))
    end = re_escape(unichr(end))
    return u"%s%s-%s" % ("".join(extra), start, end)


def _construct_regexp(pattern, mapping):
    """Raises NotImplementedError"""

    parts = []
    literals = []

    for op, av in pattern:

        if literals and op != "literal":
            parts.append(_fixup_literal_list(literals, mapping))
            del literals[:]

        if op == "not_literal":
            parts.append(_fixup_not_literal(av, mapping))
        elif op == "literal":
            literals.append(av)
            continue
        elif op == "category":
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

    assert isinstance(text, unicode)

    pattern = sre_parse.parse(text)
    return _construct_regexp(pattern, mapping)


# use _DIACRITIC_CACHE and create a lookup table
_mapping = generate_re_mapping(diacritic_for_letters(regenerate=False))

# add more from the UCA decomp dataset
for cp, repl in iteritems(_UCA_DECOMPS):
    _mapping[cp] = _mapping.get(cp, u"") + repl


def re_add_variants(text):
    """Will replace all occurrences of ascii chars
    by a bracket expression containing the character and all its
    variants with a diacritic mark.

    "föhn" -> "[fḟ]ö[hĥȟḣḥḧḩḫẖ][nñńņňǹṅṇṉṋ]"

    In case the passed in regex is invalid raises re.error.

    Supports all regexp except ones with group references. In
    case something is not supported NotImplementedError gets raised.
    """

    assert isinstance(text, unicode)

    return re_replace_literals(text, _mapping)
