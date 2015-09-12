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
    from urlparse import urlparse
    urlparse
    from urllib import pathname2url
    pathname2url
    from cStringIO import StringIO as cBytesIO
    cBytesIO

    text_type = unicode

    exec("def reraise(tp, value, tb):\n raise tp, value, tb")
elif PY3:
    import builtins
    builtins
    from urllib.parse import urlparse
    urlparse
    from urllib.request import pathname2url
    pathname2url
    from io import BytesIO as cBytesIO
    cBytesIO

    text_type = str

    def reraise(tp, value, tb):
        raise tp(value).with_traceback(tb)
