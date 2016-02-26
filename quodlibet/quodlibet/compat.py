# -*- coding: utf-8 -*-
# Copyright (C) 2013  Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

import sys


PY2 = sys.version_info[0] == 2
PY3 = not PY2

if PY2:
    import __builtin__ as builtins
    builtins
    from urlparse import urlparse, urlunparse, urlsplit
    urlparse, urlunparse, urlsplit
    from urllib import pathname2url, url2pathname, quote_plus, unquote_plus
    pathname2url, url2pathname, quote_plus, unquote_plus
    from urllib2 import urlopen
    urlopen
    from cStringIO import StringIO as cBytesIO
    cBytesIO
    from StringIO import StringIO
    StringIO
    import cPickle as pickle
    pickle
    from functools import reduce
    reduce
    from operator import div as floordiv

    xrange = xrange
    long = long

    text_type = unicode
    string_types = (str, unicode)
    integer_types = (int, long)
    number_types = (int, long, float)

    iteritems = lambda d: d.iteritems()
    itervalues = lambda d: d.itervalues()

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
elif PY3:
    import builtins
    builtins
    from urllib.parse import urlparse, urlunparse, quote_plus, unquote_plus, \
        urlsplit
    urlparse, quote_plus, unquote_plus, urlunparse, urlsplit
    from urllib.request import pathname2url, url2pathname
    pathname2url, url2pathname
    from urllib.request import urlopen
    urlopen
    from io import BytesIO as cBytesIO
    cBytesIO
    from io import StringIO
    StringIO = StringIO
    import pickle
    pickle
    from functools import reduce
    reduce
    from operator import floordiv
    floordiv

    xrange = range
    long = int

    text_type = str
    string_types = (str,)
    integer_types = (int,)
    number_types = (int, float)

    iteritems = lambda d: iter(d.items())
    itervalues = lambda d: iter(d.values())

    import builtins
    exec_ = getattr(builtins, "exec")

    def reraise(tp, value, tb):
        raise tp(value).with_traceback(tb)
