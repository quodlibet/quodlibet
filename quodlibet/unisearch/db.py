# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from typing import Dict, Set, List
import unicodedata
import sys
from urllib.request import urlopen

from quodlibet.util import cached_func


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
_UCA_DECOMPS_CACHE = {
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


_PUNCT_CONFUSABLES_CACHE = {
    u'!': u'\uff01\u01c3\u2d51',
    u'!!': u'\u203c',
    u'!?': u'\u2049',
    u'"': (u'\u1cd3\uff02\u201c\u201d\u201f\u2033\u2036\u3003\u05f4\u02dd'
           u'\u02ba\u02f6\u02ee\u05f2'),
    u'&': u'\ua778',
    u"'": (u'\u055d\uff07\u2018\u2019\u201b\u2032\u2035\u055a\u05f3`\u1fef'
           u'\uff40\xb4\u0384\u1ffd\u1fbd\u1fbf\u1ffe\u02b9\u0374\u02c8\u02ca'
           u'\u02cb\u02f4\u02bb\u02bd\u02bc\u02be\ua78c\u05d9\u07f4\u07f5'
           u'\u144a\u16cc'),
    u"''": (u'\u1cd3"\uff02\u201c\u201d\u201f\u2033\u2036\u3003\u05f4\u02dd'
            u'\u02ba\u02f6\u02ee\u05f2'),
    u"'''": u'\u2034\u2037',
    u"''''": u'\u2057',
    u'(': u'\uff3b\u2768\u2772\u3014\ufd3e',
    u'((': u'\u2e28',
    u')': u'\uff3d\u2769\u2773\u3015\ufd3f',
    u'))': u'\u2e29',
    u'*': u'\u204e\u066d\u2217\U0001031f',
    u',': u'\u060d\u066b\u201a\xb8\ua4f9',
    u'-': (u'\u2010\u2011\u2012\u2013\ufe58\u06d4\u2043\u02d7\u2212\u2796'
           u'\u2cba'),
    u'-.': u'\ua4fe',
    u'.': u'\U0001d16d\u2024\u0701\u0702\ua60e\U00010a50\u0660\u06f0\ua4f8',
    u'.,': u'\ua4fb',
    u'..': u'\u2025\ua4fa',
    u'...': u'\u2026',
    u'/': (u'\u1735\u2041\u2215\u2044\u2571\u27cb\u29f8\U0001d23a\u31d3\u3033'
           u'\u2cc6\u30ce\u4e3f\u2f03'),
    u'//': u'\u2afd',
    u'///': u'\u2afb',
    u':': (u'\u0903\u0a83\uff1a\u0589\u0703\u0704\u16ec\ufe30\u1803\u1809'
           u'\u205a\u05c3\u02f8\ua789\u2236\u02d0\ua4fd'),
    u';': u'\u037e',
    u'?': u'\u0294\u0241\u097d\u13ae\ua6eb',
    u'?!': u'\u2048',
    u'??': u'\u2047',
    u'\\': (u'\uff3c\ufe68\u2216\u27cd\u29f5\u29f9\U0001d20f\U0001d23b\u31d4'
            u'\u4e36\u2f02'),
    u'\\\\': u'\u2cf9\u244a',
    u'_': u'\u07fa\ufe4d\ufe4e\ufe4f',
    u'{': u'\u2774\U0001d114',
    u'}': u'\u2775',
}


def get_decomps_mapping(regenerate=False) -> Dict[str, str]:
    """This takes the decomps.txt file of the Unicode UCA and gives us a cases
    where a letter can be decomposed for collation and that mapping isn't in
    NFKD.
    """

    if not regenerate:
        return _UCA_DECOMPS_CACHE

    mapping: Dict[str, str] = {}

    h = urlopen("http://unicode.org/Public/UCA/8.0.0/decomps.txt")
    for line in h.read().splitlines():
        if line.startswith("#"):
            continue

        def to_uni(x):
            return chr(int(x, 16))
        def is_letter(x):
            return unicodedata.category(x) in ('Lu', 'Ll', 'Lt')

        cp, line = line.split(";", 1)
        tag, line = line.split(";", 1)
        decomp, line = line.split("#", 1)
        decomp = map(to_uni, decomp.strip().split())
        cp = to_uni(cp)

        if not is_letter(cp):
            continue

        decomp = filter(is_letter, decomp)
        simple = "".join(decomp)
        if not simple:
            continue

        # skip anything we get from normalization
        if unicodedata.normalize("NFKD", cp)[0] == simple:
            continue

        mapping[simple] = mapping.get(simple, "") + cp

    return mapping


def get_punctuation_mapping(regenerate=False) -> Dict[str, str]:
    """This takes the unicode confusables set and extracts punctuation
    which looks similar to one or more ASCII punctuation.

    e.g. ' --> ＇

    """

    if not regenerate:
        return _PUNCT_CONFUSABLES_CACHE

    h = urlopen("http://www.unicode.org/Public/security/9.0.0/confusables.txt")
    data = h.read()
    mapping: Dict[str, str] = {}
    for line in data.decode("utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(u"#"):
            continue

        char, repls = line.split(";", 2)[:2]
        char = char.strip()
        repls = repls.split()
        def to_uni(x):
            return chr(int(x, 16))
        char = to_uni(char)
        repls = [to_uni(r) for r in repls]

        def is_ascii(char):
            try:
                char.encode("ascii")
            except UnicodeEncodeError:
                return False
            return True

        def is_punct(char):
            return unicodedata.category(char).startswith("P")

        if all(is_ascii(c) and is_punct(c) for c in repls) and char:
            repls_joined = u"".join(repls)
            mapping[repls_joined] = mapping.get(repls_joined, u"") + char

    # if any of the equal chars is also ascii + punct we can replace
    # it as well
    for ascii_, uni in mapping.items():
        also_ascii = [c for c in uni if is_ascii(c) and is_punct(c)]
        for c in also_ascii:
            mapping[c] = uni.replace(c, u"")

    return mapping


def diacritic_for_letters(regenerate=False) -> Dict[str, str]:
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

    d: Dict[str, Set[str]] = {}
    for i in range(sys.maxunicode):
        u = chr(i)
        n = unicodedata.normalize("NFKD", u)
        if len(n) <= 1:
            continue
        if unicodedata.category(u) not in ("Lu", "Ll", "Lt"):
            continue
        if not all(map(unicodedata.combining, n[1:])):
            continue
        d.setdefault(n[1:], set()).add(n[0])

    d2: Dict[str, str] = {}
    for k, v in d.items():
        d2[k] = u"".join(sorted(v))

    return d2


def generate_re_mapping(_diacritic_for_letters: Dict[str, str]) -> Dict[str, str]:
    letter_to_variants: Dict[str, List[str]] = {}

    # combine combining characters with the ascii chars
    for dia, letters in _diacritic_for_letters.items():
        for c in letters:
            unichar = unicodedata.normalize("NFKC", c + dia)
            letter_to_variants.setdefault(c, []).append(unichar)

    letter_to_variants_joined: Dict[str, str] = {}
    # create strings to replace ascii with
    for k, v in letter_to_variants.items():
        letter_to_variants_joined[k] = u"".join(sorted(v))

    return letter_to_variants_joined


@cached_func
def get_replacement_mapping() -> Dict[str, List[str]]:
    """Returns a dict mapping a sequence of characters to another sequence
    of characters.

    If a key occurs in a text, it should also match any of the characters in
    in the value.
    """

    mapping: Dict[str, List[str]] = {}

    # use _DIACRITIC_CACHE and create a lookup table
    for cp, repl in generate_re_mapping(
            diacritic_for_letters(regenerate=False)).items():
        mapping.setdefault(cp, []).extend(repl)

    # add more from the UCA decomp dataset
    for cp, repl in get_decomps_mapping(regenerate=False).items():
        mapping.setdefault(cp, []).extend(repl)

    # and some punctuation
    for cp, repl in get_punctuation_mapping(regenerate=False).items():
        mapping.setdefault(cp, []).extend(repl)

    return mapping
