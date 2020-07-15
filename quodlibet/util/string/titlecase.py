# Copyright 2007 Javier Kohen
#      2010,2014 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unicodedata


# Cheat list for human title-casing in English. See Issue 424.
ENGLISH_INCORRECTLY_CAPITALISED_WORDS = \
    [u"The", u"An", u"A", u"'N'", u"'N", u"N'", u"Tha", u"De", u"Da",
     u"In", u"To", u"For", u"Up", u"With", u"As", u"At", u"From",
     u"Into", u"On", u"Out",
     #, u"Over",
     u"Of", u"By", u"'Til", u"Til",
     u"And", u"Or", u"Nor",
#    u"Is", u"Are", u"Am"
    ]

# Allow basic sentence-like concepts eg "Artist: The Greatest Hits"
ENGLISH_SENTENCE_ENDS = [".", ":", "-"]


def iswbound(char):
    """Returns whether the given character is a word boundary."""
    category = unicodedata.category(char)
    # If it's a space separator or punctuation
    return 'Zs' == category or 'Sk' == category or 'P' == category[0]


def utitle(string):
    """Title-case a string using a less destructive method than str.title."""
    new_string = string[0].capitalize()
    # It's possible we need to capitalize the second character...
    cap = iswbound(string[0])
    for i in range(1, len(string)):
        s = string[i]
        prev = string[i - 1]
        # Special case apostrophe in the middle of a word.
        # Also, extra case to deal with Irish-style names (eg O'Conner)
        if u"'" == s \
            and string[i - 1].isalpha() \
            and not (i > 1 and string[i - 2].isspace() and
                     prev.lower() == u"o"):
            cap = False
        elif iswbound(s):
            cap = True
        elif cap and s.isalpha():
            cap = False
            s = s.capitalize()
        else:
            cap = False
        new_string += s

    return new_string


def title(string, locale="utf-8"):
    """Title-case a string using a less destructive method than str.title."""
    if not string:
        return u""
    # if the string is all uppercase, lowercase it - Erich/Javier
    #   Lots of Japanese songs use entirely upper-case English titles,
    #   so I don't like this change... - JoeW
    #if string == string.upper(): string = string.lower()
    if not isinstance(string, str):
        string = string.decode(locale)
    return utitle(string)


def _humanise(text):
    """Reverts a title-cased string to a more natural (English) title-casing.
    Intended for use after util.title() only"""

    def previous_real_word(ws, idx):
        """Returns the first non-null word from words before position `idx`"""
        while idx > 0:
            idx -= 1
            if ws[idx] != "":
                break
        return ws[idx]

    words = text.split(" ")   # Yes: to preserve double spacing (!)
    for i in range(1, len(words) - 1):
        word = words[i]
        if word in ENGLISH_INCORRECTLY_CAPITALISED_WORDS:
            prev = previous_real_word(words, i)
            # Add an exception for would-be ellipses...
            if (prev and (not prev[-1] in ENGLISH_SENTENCE_ENDS
                          or prev[-3:] == '...')):
                words[i] = word.lower()
    return u" ".join(words)


def human_title(text):
    """Returns a human title-cased string, using a more natural (English)
    title-casing

     e.g. Dark night OF the Soul -> Dark Night of the Soul."""
    return _humanise(title(text))
