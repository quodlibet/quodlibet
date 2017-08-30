# -*- coding: utf-8 -*-
# Copyright 2017 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys
import platform

import quodlibet
from quodlibet.compat import text_type, urlencode
from quodlibet.util.dprint import format_exception


def build_issue_url(title, body):
    """Returns an URL which provides a pre-filled github issue.

    Args:
        title (text_type): The issue title
        body (text_type): The issue content
    Returns:
        str: the URL to open
    """

    title = text_type(title).encode("utf-8")
    body = text_type(body).encode("utf-8")
    params = urlencode([("title", title), ("body", body)])

    return "https://github.com/quodlibet/quodlibet/issues/new?%s" % params


def get_github_issue_url(exc_info):
    """Gives an URL for a pre-filled github issue based on an exception

    Returns:
        str
    """

    error_title = (text_type(exc_info[1]).strip() or u"\n").splitlines()[0]
    title = u"[Error] %s: %s" % (exc_info[0].__name__, error_title)
    error_text = u"\n".join(format_exception(*exc_info))
    body = u"""\
* What did you try to do when the error occurred?

Error Details:
```
%s

Version: %s
Python: %s
Platform: %s
```
""" % (error_text, quodlibet.get_build_description(), sys.version,
       platform.platform())

    return build_issue_url(title, body)
