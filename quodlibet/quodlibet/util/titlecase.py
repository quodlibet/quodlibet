# Copyright 2007 Javier Kohen, 2010 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import unicodedata
from quodlibet import config

TITLECASE_CONFIG_SECTION = 'editing'
TITLECASE_CONFIG_HUMAN_ENABLED = 'human_title_case'

# Cheat list for human title-casing in English. See Issue 424.
ENGLISH_INCORRECTLY_CAPITALISED_WORDS = \
    [u"The", u"An", u"A", u"'N'", u"Tha", u"De", u"Da", u"'N", u"N'",
     u"In", u"To", u"For", u"Up", u"With", u"As", u"At", u"From",
     u"Into", u"On", u"Out", u"Over",
     u"Of", u"By", u"'Til", u"Til",
     u"And", u"Or", u"Nor",
# It is not so common anymore to lowercase these.  See for example the CMS.
#    u"Is", u"Are", u"Am"
    ]
# Allow basic sentence-like concepts eg "Artist: The Greatest Hits"
ENGLISH_SENTENCE_ENDS = [".", ":", "-"]


def titlecase_config_get(key, default=''):
    try:
        return config.getboolean(TITLECASE_CONFIG_SECTION, key)
    except config.error:
        return default

def iswbound(char):
    """Returns whether the given character is a word boundary."""
    category = unicodedata.category(char)
    # If it's a space separator or punctuation
    return 'Zs' == category or 'Sk' == category or 'P' == category[0]

def previous_real_word(words, i):
    """Returns the first word from words before position i that is non-null"""
    while (i>0):
        i -= 1
        if words[i]!="": break
    return words[i]

def utitle(string):
    """Title-case a string using a less destructive method than str.title."""
    new_string = string[0].capitalize()
    # It's possible we need to capitalise the second character...
    cap = iswbound(string[0])
    for i in xrange(1, len(string)):
        s = string[i]
        prev = string[i-1]
        # Special case apostrophe in the middle of a word.
        # Also, extra case to deal with Irish-style names (eg O'Conner)
        if u"'" == s \
            and string[i-1].isalpha() \
            and not (i>1 and string[i-2].isspace() and prev.lower()==u"o"):
            cap = False
        elif iswbound(s): cap = True
        elif cap and s.isalpha():
            cap = False
            s = s.capitalize()
        else: cap = False
        new_string += s

    if titlecase_config_get(TITLECASE_CONFIG_HUMAN_ENABLED, True):
        # print_d("Using Human title casing for '%s'..." % new_string)
        words = new_string.split(" ")   # Yes: to preserve double spacing (!)
        for i in xrange(1, len(words)-1):
            word = words[i]
            if word in ENGLISH_INCORRECTLY_CAPITALISED_WORDS:
                prev = previous_real_word(words, i)
                if (not prev[-1] in ENGLISH_SENTENCE_ENDS
                # Add an exception for would-be ellipses...
                or prev[-3:]=='...'):
                    words[i] = word.lower()
        return u" ".join(words)
    else:
        return new_string

def title(string, locale="utf-8"):
    """Title-case a string using a less destructive method than str.title."""
    if not string: return u""
    # if the string is all uppercase, lowercase it - Erich/Javier
    #   Lots of Japanese songs use entirely upper-case English titles,
    #   so I don't like this change... - JoeW
    #if string == string.upper(): string = string.lower()
    if not isinstance(string, unicode):
        string = string.decode(locale)
    return utitle(string)
