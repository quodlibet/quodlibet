# -*- coding: utf-8 -*-
# Copyright 2004-2009 Joe Wreschnig, Michael Urman, Steven Robertson
#           2011,2013 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation


def isascii(string):
    """Returns if the passed str/unicode is an ascii encoded string or
    unicode string containing only ascii code points.
    """

    try:
        if isinstance(string, bytes):
            string.decode("ascii")
        else:
            string.encode("ascii")
    except UnicodeError:
        return False
    return True


def decode(s, charset="utf-8"):
    """Decode a string; if an error occurs, replace characters and append
    a note to the string."""
    try:
        return s.decode(charset)
    except UnicodeError:
        from quodlibet import _
        return s.decode(charset, "replace") + " " + _("[Invalid Encoding]")


def encode(s, charset="utf-8"):
    """Encode a string; if an error occurs, replace characters and append
    a note to the string."""
    try:
        return s.encode(charset)
    except UnicodeError:
        from quodlibet import _
        return (s + " " + _("[Invalid Encoding]")).encode(charset, "replace")


def split_escape(string, sep, maxsplit=None, escape_char="\\"):
    """Like unicode/str.split but allows for the separator to be escaped

    If passed unicode/str will only return list of unicode/str.

    Borrowed from Mutagen's mid3v2
    """

    assert len(sep) == 1
    assert len(escape_char) == 1

    # don't allow auto decoding of 'string'
    if isinstance(string, bytes):
        assert not isinstance(sep, unicode)

    if maxsplit is None:
        maxsplit = len(string)

    empty = type(string)("")
    result = []
    current = empty
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
                current = empty
            else:
                current += char
    result.append(current)
    return result


def join_escape(values, sep, escape_char="\\"):
    """Join str/unicode so that it can be split with split_escape.

    In case values is empty, the result has the type of `sep`.
    otherwise it has the type of values.

    Be aware that split_escape(join_escape([])) will result in [''].
    """

    assert len(sep) == 1
    assert len(escape_char) == 1

    # don't allow auto decoding of 'values'
    if values and isinstance(values[0], bytes):
        assert not isinstance(sep, unicode)

    escaped = []
    for value in values:
        value = value.replace(escape_char, escape_char + escape_char)
        value = value.replace(sep, escape_char + sep)
        escaped.append(value)
    return sep.join(escaped)
