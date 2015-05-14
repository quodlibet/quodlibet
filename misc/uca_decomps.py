#!/usr/bin/python2
# -*- coding: utf-8 -*-

"""This takes the decomps.txt file of the Unicode UCA and gives us a cases
where a letter can be decomposed for collation and that mapping isn't in NFKD.

See quodlibet.query._diacritic
"""

import unicodedata

mapping = {}

# See http://unicode.org/Public/UCA/latest/decomps.txt
with open("decomps.txt", "rb") as h:
    for line in h.read().splitlines():
        if line.startswith("#"):
            continue

        to_uni = lambda x: unichr(int(x, 16))
        is_letter = lambda x: unicodedata.category(x) in ("Lu", "Ll", "Lt")

        cp, line = line.split(";", 1)
        tag, line = line.split(";", 1)
        decomp, line = line.split("#", 1)
        decomp = map(to_uni, decomp.strip().split())
        cp = to_uni(cp)

        if not is_letter(cp):
            continue

        letter_count = sum((is_letter(c) for c in decomp))
        if letter_count != 1 or not is_letter(decomp[0]):
            continue
        simple = decomp[0]

        # skip anything we get from normalization
        if unicodedata.normalize("NFKD", cp)[0] == simple:
            continue

        mapping[simple] = mapping.get(simple, "") + cp

for key, values in mapping.items():
    print key, " ->", values

import pprint
pprint.pprint(mapping)
