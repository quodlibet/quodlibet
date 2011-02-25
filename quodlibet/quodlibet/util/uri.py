# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

# TODO:
#  * netloc separation (user/passwd/host/port using urllib)
#  * Coerce a URI to Unicode (via an encoding for the path and
#    Punycode for the domain) and back.

import re

from urllib import url2pathname, quote_plus, unquote_plus
from urlparse import urlparse, urlunparse

from quodlibet.util import pathname2url

class URI(str):
    """A full URI string. This object provides several convenience
    attributes to access data from the urlparse and urllib modules.

    URIs inherit from str, and so any method that works on a str
    works on a URI.

    URIs are not closed under concatenation, slicing, and so on. Neither
    are these URI objects; such operations will return strs."""

    def __new__(klass, value, escaped=True):
        """Create a new URI object. By default, the URI is assumed to be
        escaped already. Pass escaped=False if you need the URI escaped
        (this is imperfect now).

        The URI returned will be equivalent, but not necessarily
        equal, to the value passed in."""

        # URIs like file:////home/foo/... are valid, since
        # //home/foo is a valid path. But urlparse parses this
        # into a netloc of home and a path of /foo. Lame.
        value = re.sub("^([A-Za-z]+):///+", "\\1:///", value)

        values = list(urlparse(value))
        if not escaped:
            # FIXME: Handle netloc
            # FIXME: Handle query args
            values[2] = quote_plus(values[2], safe="/~")
        value = urlunparse(values)
        obj = str.__new__(klass, value)
        if not obj.scheme:
            raise ValueError("URIs must have a scheme, such as 'http://'")
        elif not (obj.netloc or obj.path):
            raise ValueError("URIs must have a network location or path")
        else: return obj

    def frompath(klass, value):
        """Construct a URI from an unescaped filename."""
        # windows unicode path chars may break pathname2url; encode in UTF-8
        if isinstance(value, unicode): value = value.encode("UTF-8")
        return klass("file://" + pathname2url(value), escaped=True)
    frompath = classmethod(frompath)

    scheme = property(lambda self: urlparse(self)[0],
                      None, None, "URI scheme (e.g. 'http')")
    netloc = property(lambda self: urlparse(self)[1], None, None,
                      "URI network location (e.g. 'example.com:21')")
    path = property(lambda self: urlparse(self)[2],
                    None, None, "URI path (e.g. '/~user')")
    params = property(lambda self: urlparse(self)[3],
                      None, None, "URI parameters")
    query = property(lambda self: urlparse(self)[4],
                     None, None, "URI query string (e.g. 'foo=bar&a=b')")
    fragment = property(lambda self: urlparse(self)[5],
                        None, None, "URI fragment ('foo' in '#foo')")

    def unescaped(self):
        values = list(urlparse(self))
        values[2] = unquote_plus(values[2])
        return urlunparse(values)
    unescaped = property(unescaped, None, None,
                         "an unescaped str (not URI) version of the URI")

    def filename(self):
        if self.scheme != "file":
            raise ValueError("only the file scheme supports filenames")
        elif self.netloc:
            raise ValueError("only local files have filenames")
        else: return url2pathname(self.path)
    filename = property(filename, None, None,
                        "a local filename equivalent to the URI")

    is_filename = property(
        lambda s: s.scheme == "file" and not s.netloc, None, None,
        "True if the URI is a valid (not necessarily existing) local filename")

    def __repr__(self):
        return "%s(%r)" % (type(self).__name__, self.unescaped)
