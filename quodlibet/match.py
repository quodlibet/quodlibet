# Copyright 2004 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

# True if the object matches any of its REs.
class Union(object):
    def __init__(self, res):
        self.res = res

    def search(self, data):
        for re in self.res:
            if re.search(data): return True
        return False

    def __repr__(self):
        return "<Union \n " + "\n ".join(map(repr, self.res)) + ">"

# True if the object matches all of its REs.
class Inter(object):
    def __init__(self, res):
        self.res = res

    def search(self, data):
        for re in self.res:
            if not re.search(data): return False
        return True

    def __repr__(self):
        return "<Inter \n " + "\n ".join(map(repr, self.res)) + ">"

# True if the object doesn't match its RE.
class Neg(object):
    def __init__(self, re):
        self.re = re

    def search(self, data):
        return not self.re.search(data)

    def __repr__(self):
        return "<Neg " + repr(self.re) + ">"

# See if a property of the object matches its RE.
class Tag(object):

    # Shorthand for common tags.
    ABBRS = { "a": "artist",
              "b": "album",
              "v": "version",
              "t": "title",
              "n": "tracknumber",
              "d": "date",
              }
    def __init__(self, names, res):
        self.names = [Tag.ABBRS.get(n.lower(), n.lower()) for n in names]
        self.res = res
        if "*" in self.names:
            self.names.remove("*")
            self.names.extend(["artist", "album", "title", "version"])
        if not isinstance(self.res, list): self.res = [self.res]

    def search(self, data):
        for name in self.names:
            for re in self.res:
                if re.search(data.get(name, data.get("~"+name, ""))):
                    return True
        return False

    def __repr__(self):
        return ("<Tag names=(" + ",".join(self.names) + ") \n " +
                "\n ".join(map(repr, self.res)) + ">")
