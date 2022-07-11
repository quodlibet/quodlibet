# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import sys
import tempfile
from functools import wraps

from senf import path2fsn


from .environment import is_linux


def cmp(a, b):
    return (a > b) - (a < b)


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


def hashable(cls):
    """Makes sure the class is hashable.

    Needs a working __eq__ and __hash__ and will add a __ne__.
    """

    # py2
    assert "__hash__" in cls.__dict__
    # py3
    assert cls.__dict__["__hash__"] is not None
    assert "__eq__" in cls.__dict__

    cls.__ne__ = lambda self, other: not self.__eq__(other)

    return cls


def get_module_dir(module=None):
    """Returns the absolute path of a module. If no module is given
    the one this is called from is used.
    """

    if module is None:
        file_path = sys._getframe(1).f_globals["__file__"]
    else:
        file_path = getattr(module, "__file__")
    file_path = path2fsn(file_path)
    return os.path.dirname(os.path.realpath(file_path))


def get_ca_file():
    """A path to a CA file or None.

    Depends whether we use certifi or the system trust store
    on the current platform.
    """

    if is_linux():
        return None

    import certifi

    return os.path.join(get_module_dir(certifi), "cacert.pem")


def NamedTemporaryFile(*args, **kwargs):
    """Like tempfile.NamedTemporaryFile, but supports unicode paths on
    Py2+Windows
    """

    return tempfile.NamedTemporaryFile(*args, **kwargs)
