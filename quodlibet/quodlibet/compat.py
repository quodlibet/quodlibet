# -*- coding: utf-8 -*-
# Copyright (C) 2013  Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys


PY2 = sys.version_info[0] == 2
PY3 = not PY2

if PY2:
    import __builtin__ as builtins
    builtins
    from urlparse import urlparse, urlunparse, urlsplit, parse_qs
    urlparse, urlunparse, urlsplit, parse_qs
    from urllib import pathname2url, url2pathname, quote_plus, unquote_plus, \
        urlencode, quote, unquote
    pathname2url, url2pathname, quote_plus, unquote_plus, urlencode, quote, \
        unquote
    from urllib2 import urlopen, build_opener
    urlopen, build_opener
    from cStringIO import StringIO as cBytesIO
    cBytesIO
    from StringIO import StringIO
    StringIO
    from functools import reduce
    reduce
    from operator import div as floordiv
    from itertools import izip_longest, izip
    izip_longest, izip
    import Queue as queue
    queue

    xrange = xrange
    long = long
    unichr = unichr
    cmp = cmp

    getbyte = lambda b, i: b[i]
    iterbytes = lambda b: iter(b)

    text_type = unicode
    string_types = (str, unicode)
    integer_types = (int, long)
    number_types = (int, long, float)

    iteritems = lambda d: d.iteritems()
    itervalues = lambda d: d.itervalues()
    iterkeys = lambda d: d.iterkeys()
    listitems = lambda d: d.items()
    listkeys = lambda d: d.keys()
    listvalues = lambda d: d.values()

    listfilter = filter
    listmap = map

    def exec_(_code_, _globs_=None, _locs_=None):
        if _globs_ is None:
            frame = sys._getframe(1)
            _globs_ = frame.f_globals
            if _locs_ is None:
                _locs_ = frame.f_locals
            del frame
        elif _locs_ is None:
            _locs_ = _globs_
        exec("""exec _code_ in _globs_, _locs_""")

    exec("def reraise(tp, value, tb):\n raise tp, value, tb")

    def swap_to_string(cls):
        if "__str__" in cls.__dict__:
            cls.__unicode__ = cls.__str__

        if "__bytes__" in cls.__dict__:
            cls.__str__ = cls.__bytes__

        return cls

    escape_decode = lambda b: b.decode("string-escape")

elif PY3:
    import builtins
    builtins
    from urllib.parse import urlparse, urlunparse, quote_plus, unquote_plus, \
        urlsplit, parse_qs, urlencode, quote, unquote
    urlparse, quote_plus, unquote_plus, urlunparse, urlsplit, parse_qs, \
        urlencode, quote, unquote
    from urllib.request import pathname2url, url2pathname
    pathname2url, url2pathname
    from urllib.request import urlopen, build_opener
    urlopen, build_opener
    from io import BytesIO as cBytesIO
    cBytesIO
    from io import StringIO
    StringIO
    from functools import reduce
    reduce
    from operator import floordiv
    floordiv
    from itertools import zip_longest as izip_longest
    izip_longest
    import codecs
    import queue
    queue

    xrange = range
    long = int
    unichr = chr
    cmp = lambda a, b: (a > b) - (a < b)
    izip = zip

    getbyte = lambda b, i: b[i:i + 1]
    iterbytes = lambda b: (bytes([v]) for v in b)

    text_type = str
    string_types = (str,)
    integer_types = (int,)
    number_types = (int, float)

    iteritems = lambda d: iter(d.items())
    itervalues = lambda d: iter(d.values())
    iterkeys = lambda d: iter(d.keys())
    listitems = lambda d: list(d.items())
    listkeys = lambda d: list(d.keys())
    listvalues = lambda d: list(d.values())

    listfilter = lambda *x: list(filter(*x))
    listmap = lambda *x: list(map(*x))

    import builtins
    exec_ = getattr(builtins, "exec")

    def reraise(tp, value, tb):
        raise tp(value).with_traceback(tb)

    def swap_to_string(cls):
        return cls

    escape_decode = lambda b: codecs.escape_decode(b)[0]  # type: ignore


# taken from six
def add_metaclass(metaclass):
    """Class decorator for creating a class with a metaclass."""

    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        slots = orig_vars.get('__slots__')
        if slots is not None:
            if isinstance(slots, str):
                slots = [slots]
            for slots_var in slots:
                orig_vars.pop(slots_var)
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper
