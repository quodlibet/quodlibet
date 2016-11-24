# -*- coding: utf-8 -*-
# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import locale
from functools import wraps

from senf import environ, argv


environ, argv


def cached_func(f):
    """Decorator which caches the return value of a function which
    doesn't take any input.
    """

    res = []

    @wraps(f)
    def wrapper():
        if not res:
            res.append(f())
        return res[0]
    return wrapper


def _verify_encoding(encoding):
    try:
        u"".encode(encoding)
    except LookupError:
        encoding = "utf-8"
    return encoding


@cached_func
def get_locale_encoding():
    """Returns the encoding defined by the locale"""

    try:
        encoding = locale.getpreferredencoding()
    except locale.Error:
        encoding = "utf-8"
    else:
        # python on macports can return a bugs result (empty string)
        encoding = _verify_encoding(encoding)

    return encoding


def total_ordering(cls):
    """Adds all possible ordering methods to a class.

    Needs a working __eq__ and __lt__ and will supply the rest.
    """

    assert "__eq__" in cls.__dict__
    assert "__lt__" in cls.__dict__

    cls.__le__ = lambda self, other: self == other or self < other
    cls.__gt__ = lambda self, other: not (self == other or self < other)
    cls.__ge__ = lambda self, other: not self < other
    cls.__ne__ = lambda self, other: not self.__eq__(other)

    return cls
