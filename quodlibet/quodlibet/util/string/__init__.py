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
