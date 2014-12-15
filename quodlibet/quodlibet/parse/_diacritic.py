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
diacritics. This allows to match e.g. "Múm" using "Mum".

re_add_diacritics(u"Mum") => u"[MḾṀṂ][uùúûüũūŭůűųưǔǖǘǚǜȕȗṳṵṷṹṻụủứừửữự][mḿṁṃ]"
"""

import unicodedata
import sys


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


def diacritic_for_letters(regenerate=False):
    """Returns a mapping for combining diacritics to ascii characters
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


def replace_re(string, mapping):
    """Replace a character in a regexp with one or more other ones.

    FIXME: support ranges
    """

    assert isinstance(string, unicode)

    done = []
    escaped = False
    for c in string:
        if escaped:
            escaped = False
            done.append(c)
        else:
            if c == u"\\":
                escaped = True
                done.append(c)
            else:
                if c in mapping:
                    done.append(u"[%s]" % mapping[c])
                else:
                    done.append(c)
    return u"".join(done)


def generate_re_diacritic_func(_diacritic_for_letters):
    """Returns a function which will replace all occurrences of ascii chars
    by a bracket expression containing the character and all its
    variants with diacriticals.

    "föhn" -> "[fḟ]ö[hĥȟḣḥḧḩḫẖ][nñńņňǹṅṇṉṋ]"

    TODO: Ideally this should parse the regexp and ignore ranges etc.
    Using sre_parse is an option, but editing the resulting parse tree
    depends on too many internals.
    """

    letter_to_variants = {}

    # combine combining characters with the ascii chars
    for dia, letters in _diacritic_for_letters.iteritems():
        for c in letters:
            unichar = unicodedata.normalize("NFKC", c + dia)
            letter_to_variants.setdefault(c, []).append(unichar)

    # create strings to replace ascii with
    for k, v in letter_to_variants.items():
        letter_to_variants[k] = k + u"".join(sorted(v))

    def replace_func(string):
        return replace_re(string, letter_to_variants)

    return replace_func


re_add_diacritics = generate_re_diacritic_func(
    diacritic_for_letters(regenerate=False))
