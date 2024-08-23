# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unicodedata
import sys
from urllib.request import urlopen

from quodlibet.util import cached_func


_DIACRITIC_CACHE = {
    "\u0300": ("AEINOUWYaeinouwy\u0391\u0395\u0397\u0399\u039f\u03a5\u03a9"
                "\u03b1\u03b5\u03b7\u03b9\u03bf\u03c5\u03c9\u0415\u0418"
                "\u0435\u0438"),
    "\u0300\u0345": "\u03b1\u03b7\u03c9",
    "\u0301": ("ACEGIKLMNOPRSUWYZacegiklmnoprsuwyz\xc6\xd8\xe6\xf8\u0391"
                "\u0395\u0397\u0399\u039f\u03a5\u03a9\u03b1\u03b5\u03b7"
                "\u03b9\u03bf\u03c5\u03c9\u0413\u041a\u0433\u043a"),
    "\u0301\u0307": "Ss",
    "\u0301\u0345": "\u03b1\u03b7\u03c9",
    "\u0302": "ACEGHIJOSUWYZaceghijosuwyz",
    "\u0302\u0300": "AEOaeo",
    "\u0302\u0301": "AEOaeo",
    "\u0302\u0303": "AEOaeo",
    "\u0302\u0309": "AEOaeo",
    "\u0303": "AEINOUVYaeinouvy",
    "\u0303\u0301": "OUou",
    "\u0303\u0304": "Oo",
    "\u0303\u0308": "Oo",
    "\u0304": ("AEGIOUYaegiouy\xc6\xe6\u0391\u0399\u03a5\u03b1\u03b9"
                "\u03c5\u0418\u0423\u0438\u0443"),
    "\u0304\u0300": "EOeo",
    "\u0304\u0301": "EOeo",
    "\u0304\u0308": "Uu",
    "\u0306": ("AEGIOUaegiou\u0391\u0399\u03a5\u03b1\u03b9\u03c5\u0410"
                "\u0415\u0416\u0418\u0423\u0430\u0435\u0436\u0438\u0443"),
    "\u0306\u0300": "Aa",
    "\u0306\u0301": "Aa",
    "\u0306\u0303": "Aa",
    "\u0306\u0309": "Aa",
    "\u0307": "ABCDEFGHIMNOPRSTWXYZabcdefghmnoprstwxyz",
    "\u0307\u0304": "AOao",
    "\u0308": ("AEHIOUWXYaehiotuwxy\u0399\u03a5\u03b9\u03c5\u0406\u0410"
                "\u0415\u0416\u0417\u0418\u041e\u0423\u0427\u042b\u042d"
                "\u0430\u0435\u0436\u0437\u0438\u043e\u0443\u0447\u044b"
                "\u044d\u0456\u04d8\u04d9\u04e8\u04e9"),
    "\u0308\u0300": "Uu\u03b9\u03c5",
    "\u0308\u0301": "IUiu\u03b9\u03c5",
    "\u0308\u0304": "AOUaou",
    "\u0308\u030c": "Uu",
    "\u0308\u0342": "\u03b9\u03c5",
    "\u0309": "AEIOUYaeiouy",
    "\u030a": "AUauwy",
    "\u030a\u0301": "Aa",
    "\u030b": "OUou\u0423\u0443",
    "\u030c": "ACDEGHIKLNORSTUZacdeghijklnorstuz\u01b7\u0292",
    "\u030c\u0307": "Ss",
    "\u030f": "AEIORUaeioru\u0474\u0475",
    "\u0311": "AEIORUaeioru",
    "\u0313": ("\u0391\u0395\u0397\u0399\u039f\u03a9\u03b1\u03b5\u03b7"
                "\u03b9\u03bf\u03c1\u03c5\u03c9"),
    "\u0313\u0300": ("\u0391\u0395\u0397\u0399\u039f\u03a9\u03b1\u03b5"
                      "\u03b7\u03b9\u03bf\u03c5\u03c9"),
    "\u0313\u0300\u0345": "\u0391\u0397\u03a9\u03b1\u03b7\u03c9",
    "\u0313\u0301": ("\u0391\u0395\u0397\u0399\u039f\u03a9\u03b1\u03b5"
                      "\u03b7\u03b9\u03bf\u03c5\u03c9"),
    "\u0313\u0301\u0345": "\u0391\u0397\u03a9\u03b1\u03b7\u03c9",
    "\u0313\u0342": "\u0391\u0397\u0399\u03a9\u03b1\u03b7\u03b9\u03c5\u03c9",
    "\u0313\u0342\u0345": "\u0391\u0397\u03a9\u03b1\u03b7\u03c9",
    "\u0313\u0345": "\u0391\u0397\u03a9\u03b1\u03b7\u03c9",
    "\u0314": ("\u0391\u0395\u0397\u0399\u039f\u03a1\u03a5\u03a9\u03b1"
                "\u03b5\u03b7\u03b9\u03bf\u03c1\u03c5\u03c9"),
    "\u0314\u0300": ("\u0391\u0395\u0397\u0399\u039f\u03a5\u03a9\u03b1"
                      "\u03b5\u03b7\u03b9\u03bf\u03c5\u03c9"),
    "\u0314\u0300\u0345": "\u0391\u0397\u03a9\u03b1\u03b7\u03c9",
    "\u0314\u0301": ("\u0391\u0395\u0397\u0399\u039f\u03a5\u03a9\u03b1"
                      "\u03b5\u03b7\u03b9\u03bf\u03c5\u03c9"),
    "\u0314\u0301\u0345": "\u0391\u0397\u03a9\u03b1\u03b7\u03c9",
    "\u0314\u0342": ("\u0391\u0397\u0399\u03a5\u03a9\u03b1\u03b7\u03b9"
                      "\u03c5\u03c9"),
    "\u0314\u0342\u0345": "\u0391\u0397\u03a9\u03b1\u03b7\u03c9",
    "\u0314\u0345": "\u0391\u0397\u03a9\u03b1\u03b7\u03c9",
    "\u031b": "OUou",
    "\u031b\u0300": "OUou",
    "\u031b\u0301": "OUou",
    "\u031b\u0303": "OUou",
    "\u031b\u0309": "OUou",
    "\u031b\u0323": "OUou",
    "\u0323": "ABDEHIKLMNORSTUVWYZabdehiklmnorstuvwyz",
    "\u0323\u0302": "AEOaeo",
    "\u0323\u0304": "LRlr",
    "\u0323\u0306": "Aa",
    "\u0323\u0307": "Ss",
    "\u0324": "Uu",
    "\u0325": "Aa",
    "\u0326": "STst",
    "\u0327": "CDEGHKLNRSTcdeghklnrst",
    "\u0327\u0301": "Cc",
    "\u0327\u0306": "Ee",
    "\u0328": "AEIOUaeiou",
    "\u0328\u0304": "Oo",
    "\u032d": "DELNTUdelntu",
    "\u032e": "Hh",
    "\u0330": "EIUeiu",
    "\u0331": "BDKLNRTZbdhklnrtz",
    "\u0342": "\u03b1\u03b7\u03b9\u03c5\u03c9",
    "\u0342\u0345": "\u03b1\u03b7\u03c9",
    "\u0345": "\u0391\u0397\u03a9\u03b1\u03b7\u03c9"
}

# See misc/uca_decomps.py
_UCA_DECOMPS_CACHE = {
    "AA": "\ua732",
    "AE": "\xc6\u01e2\u01fc",
    "AO": "\ua734",
    "AU": "\ua736",
    "AV": "\ua738\ua73a",
    "AY": "\ua73c",
    "D": "\xd0\u0110\ua779",
    "DZ": "\u01c4\u01f1",
    "Dz": "\u01c5\u01f2",
    "F": "\ua77b",
    "G": "\ua77d",
    "H": "\u0126",
    "IJ": "\u0132",
    "L": "\u0141",
    "LJ": "\u01c7",
    "LL": "\u1efa",
    "Lj": "\u01c8",
    "NJ": "\u01ca",
    "Nj": "\u01cb",
    "O": "\xd8\u01fe",
    "OE": "\u0152",
    "OO": "\ua74e",
    "R": "\ua782",
    "S": "\ua784",
    "SS": "\u1e9e",
    "T": "\ua786",
    "Tz": "\ua728",
    "VY": "\ua760",
    "aa": "\ua733",
    "ae": "\xe6\u01e3\u01fd",
    "ao": "\ua735",
    "au": "\ua737",
    "av": "\ua739\ua73b",
    "ay": "\ua73d",
    "d": "\xf0\u0111\ua77a",
    "db": "\u0238",
    "dz": "\u01c6\u01f3\u02a3",
    "d\u0291": "\u02a5",
    "d\u0292": "\u02a4",
    "f": "\ua77c",
    "ff": "\ufb00",
    "ffi": "\ufb03",
    "ffl": "\ufb04",
    "fi": "\ufb01",
    "fl": "\ufb02",
    "f\u014b": "\u02a9",
    "g": "\u1d79",
    "h": "\u0127\u210f",
    "ij": "\u0133",
    "l": "\u0142",
    "lj": "\u01c9",
    "ll": "\u1efb",
    "ls": "\u02aa",
    "lz": "\u02ab",
    "n": "\u0149",
    "nj": "\u01cc",
    "o": "\xf8\u01ff",
    "oe": "\u0153",
    "oo": "\ua74f",
    "qp": "\u0239",
    "r": "\ua783",
    "s": "\ua785",
    "ss": "\xdf",
    "st": "\ufb05\ufb06",
    "t": "\ua787",
    "th": "\u1d7a",
    "ts": "\u01be\u02a6",
    "tz": "\ua729",
    "t\u0255": "\u02a8",
    "t\u0283": "\u02a7",
    "vy": "\ua761",
    "zw": "\u018d",
    "\u039a\u03b1\u03b9": "\u03cf",
    "\u03ba\u03b1\u03b9": "\u03d7",
    "\u03c3": "\u03c2\u03f2\U0001d6d3\U0001d70d"
               "\U0001d747\U0001d781\U0001d7bb",
    "\u0413": "\u0490",
    "\u041e": "\ua668\ua66a\ua66c",
    "\u0433": "\u0491",
    "\u043e": "\ua669\ua66b\ua66d",
    "\u0565\u0582": "\u0587",
    "\u0574\u0565": "\ufb14",
    "\u0574\u056b": "\ufb15",
    "\u0574\u056d": "\ufb17",
    "\u0574\u0576": "\ufb13",
    "\u057e\u0576": "\ufb16",
    "\u2c95\u2c81\u2c93": "\u2ce4",
}


_PUNCT_CONFUSABLES_CACHE = {
    "!": "\uff01\u01c3\u2d51",
    "!!": "\u203c",
    "!?": "\u2049",
    '"': ("\u1cd3\uff02\u201c\u201d\u201f\u2033\u2036\u3003\u05f4\u02dd"
           "\u02ba\u02f6\u02ee\u05f2"),
    "&": "\ua778",
    "'": ("\u055d\uff07\u2018\u2019\u201b\u2032\u2035\u055a\u05f3`\u1fef"
           "\uff40\xb4\u0384\u1ffd\u1fbd\u1fbf\u1ffe\u02b9\u0374\u02c8\u02ca"
           "\u02cb\u02f4\u02bb\u02bd\u02bc\u02be\ua78c\u05d9\u07f4\u07f5"
           "\u144a\u16cc"),
    "''": ('\u1cd3"\uff02\u201c\u201d\u201f\u2033\u2036\u3003\u05f4\u02dd'
            '\u02ba\u02f6\u02ee\u05f2'),
    "'''": "\u2034\u2037",
    "''''": "\u2057",
    "(": "\uff3b\u2768\u2772\u3014\ufd3e",
    "((": "\u2e28",
    ")": "\uff3d\u2769\u2773\u3015\ufd3f",
    "))": "\u2e29",
    "*": "\u204e\u066d\u2217\U0001031f",
    ",": "\u060d\u066b\u201a\xb8\ua4f9",
    "-": ("\u2010\u2011\u2012\u2013\ufe58\u06d4\u2043\u02d7\u2212\u2796"
           "\u2cba"),
    "-.": "\ua4fe",
    ".": "\U0001d16d\u2024\u0701\u0702\ua60e\U00010a50\u0660\u06f0\ua4f8",
    ".,": "\ua4fb",
    "..": "\u2025\ua4fa",
    "...": "\u2026",
    "/": ("\u1735\u2041\u2215\u2044\u2571\u27cb\u29f8\U0001d23a\u31d3\u3033"
           "\u2cc6\u30ce\u4e3f\u2f03"),
    "//": "\u2afd",
    "///": "\u2afb",
    ":": ("\u0903\u0a83\uff1a\u0589\u0703\u0704\u16ec\ufe30\u1803\u1809"
           "\u205a\u05c3\u02f8\ua789\u2236\u02d0\ua4fd"),
    ";": "\u037e",
    "?": "\u0294\u0241\u097d\u13ae\ua6eb",
    "?!": "\u2048",
    "??": "\u2047",
    "\\": ("\uff3c\ufe68\u2216\u27cd\u29f5\u29f9\U0001d20f\U0001d23b\u31d4"
            "\u4e36\u2f02"),
    "\\\\": "\u2cf9\u244a",
    "_": "\u07fa\ufe4d\ufe4e\ufe4f",
    "{": "\u2774\U0001d114",
    "}": "\u2775",
}


def get_decomps_mapping(regenerate=False) -> dict[str, str]:
    """This takes the decomps.txt file of the Unicode UCA and gives us a cases
    where a letter can be decomposed for collation and that mapping isn't in
    NFKD.
    """

    if not regenerate:
        return _UCA_DECOMPS_CACHE

    mapping: dict[str, str] = {}

    h = urlopen("http://unicode.org/Public/UCA/8.0.0/decomps.txt")
    for line in h.read().splitlines():
        if line.startswith("#"):
            continue

        def to_uni(x):
            return chr(int(x, 16))
        def is_letter(x):
            return unicodedata.category(x) in ("Lu", "Ll", "Lt")

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


def get_punctuation_mapping(regenerate=False) -> dict[str, str]:
    """This takes the unicode confusables set and extracts punctuation
    which looks similar to one or more ASCII punctuation.

    e.g. ' --> ＇

    """

    if not regenerate:
        return _PUNCT_CONFUSABLES_CACHE

    h = urlopen("http://www.unicode.org/Public/security/9.0.0/confusables.txt")
    data = h.read()
    mapping: dict[str, str] = {}
    for line in data.decode("utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
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
            repls_joined = "".join(repls)
            mapping[repls_joined] = mapping.get(repls_joined, "") + char

    # if any of the equal chars is also ascii + punct we can replace
    # it as well
    for uni in mapping.values():
        also_ascii = [c for c in uni if is_ascii(c) and is_punct(c)]
        for c in also_ascii:
            mapping[c] = uni.replace(c, "")

    return mapping


def diacritic_for_letters(regenerate=False) -> dict[str, str]:
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

    d: dict[str, set[str]] = {}
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

    d2: dict[str, str] = {}
    for k, v in d.items():
        d2[k] = "".join(sorted(v))

    return d2


def generate_re_mapping(_diacritic_for_letters: dict[str, str]) -> dict[str, str]:
    letter_to_variants: dict[str, list[str]] = {}

    # combine combining characters with the ascii chars
    for dia, letters in _diacritic_for_letters.items():
        for c in letters:
            unichar = unicodedata.normalize("NFKC", c + dia)
            letter_to_variants.setdefault(c, []).append(unichar)

    letter_to_variants_joined: dict[str, str] = {}
    # create strings to replace ascii with
    for k, v in letter_to_variants.items():
        letter_to_variants_joined[k] = "".join(sorted(v))

    return letter_to_variants_joined


@cached_func
def get_replacement_mapping() -> dict[str, list[str]]:
    """Returns a dict mapping a sequence of characters to another sequence
    of characters.

    If a key occurs in a text, it should also match any of the characters in
    in the value.
    """

    mapping: dict[str, list[str]] = {}

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
