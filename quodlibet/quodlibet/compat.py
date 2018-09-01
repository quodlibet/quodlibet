# -*- coding: utf-8 -*-
# Copyright (C) 2013  Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

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
