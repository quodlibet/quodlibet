# Copyright 2016 Christoph Reiter
#
# SPDX-License-Identifier: GPL-2.0-or-later

# ruff: noqa

import sys


PY2 = sys.version_info[0] == 2
PY3 = not PY2


if PY2:
    from urlparse import urlparse, urlunparse

    urlparse, urlunparse
    from urllib import quote, unquote

    quote, unquote

    from StringIO import StringIO

    BytesIO = StringIO
    from io import StringIO as TextIO

    TextIO

    string_types = (str, unicode)
    text_type = unicode

    iteritems = lambda d: d.iteritems()
elif PY3:
    from urllib.parse import urlparse, quote, unquote, urlunparse

    urlparse, quote, unquote, urlunparse

    from io import StringIO

    StringIO = StringIO
    TextIO = StringIO
    from io import BytesIO

    BytesIO = BytesIO

    string_types = (str,)
    text_type = str

    iteritems = lambda d: iter(d.items())
