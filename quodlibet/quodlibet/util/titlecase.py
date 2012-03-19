# Copyright 2007 Javier Kohen, 2010 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import unicodedata

def iswbound(char):
    """Returns whether the given character is a word boundary."""
    category = unicodedata.category(char)
    # If it's a space separator or punctuation
    return 'Zs' == category or 'Sk' == category or 'P' == category[0]

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
