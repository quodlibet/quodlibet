# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation


def dbus_unicode_validate(text):
    """Takes a unicode string and replaces all invalid codepoints that would
    lead to errors if passed to dbus"""

    assert isinstance(text, unicode)

    # https://bugs.freedesktop.org/show_bug.cgi?id=40817
    def valid(c):
        return (c < 0x110000 and
                (c & 0xFFFFF800) != 0xD800 and
                (c < 0xFDD0 or c > 0xFDEF) and
                (c & 0xFFFE) != 0xFFFE)

    cps = []
    for c in map(ord, text):
        if valid(c):
            cps.append(c)
        else:
            cps.append(0xFFFD)
    return u"".join(map(unichr, cps))
