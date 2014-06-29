# Copyright 2004-2009 Joe Wreschnig, Michael Urman, Steven Robertson
#           2011,2013 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation


def decode(s, charset="utf-8"):
    """Decode a string; if an error occurs, replace characters and append
    a note to the string."""
    try:
        return s.decode(charset)
    except UnicodeError:
        return s.decode(charset, "replace") + " " + _("[Invalid Encoding]")


def encode(s, charset="utf-8"):
    """Encode a string; if an error occurs, replace characters and append
    a note to the string."""
    try:
        return s.encode(charset)
    except UnicodeError:
        return (s + " " + _("[Invalid Encoding]")).encode(charset, "replace")


def split_escape(string, sep, maxsplit=None, escape_char=u"\\"):
    """Like unicode.split but allows for the separator to be escaped
       Borrowed from Mutagen's mid3v2
    """

    assert len(sep) == 1
    assert len(escape_char) == 1

    if maxsplit is None:
        maxsplit = len(string)

    result = []
    current = u""
    escaped = False
    for char in string:
        if escaped:
            if char != escape_char and char != sep:
                current += escape_char
            current += char
            escaped = False
        else:
            if char == escape_char:
                escaped = True
            elif char == sep and len(result) < maxsplit:
                result.append(current)
                current = u""
            else:
                current += char
    result.append(current)
    return result
