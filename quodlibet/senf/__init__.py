# Copyright 2016 Christoph Reiter
#
# SPDX-License-Identifier: GPL-2.0-or-later

from ._fsnative import (
    fsnative,
    path2fsn,
    fsn2text,
    fsn2bytes,
    bytes2fsn,
    uri2fsn,
    fsn2uri,
    text2fsn,
    fsn2norm,
)
from ._print import print_, input_, supports_ansi_escape_codes
from ._stdlib import (
    sep,
    pathsep,
    curdir,
    pardir,
    altsep,
    extsep,
    devnull,
    defpath,
    getcwd,
    expanduser,
    expandvars,
)
from ._environ import environ, getenv, unsetenv, putenv


(
    fsnative,
    print_,
    getcwd,
    getenv,
    unsetenv,
    putenv,
    environ,
    expandvars,
    path2fsn,
    fsn2text,
    fsn2bytes,
    bytes2fsn,
    uri2fsn,
    fsn2uri,
    input_,
    expanduser,
    text2fsn,
    supports_ansi_escape_codes,
    fsn2norm,
)


version = (1, 5, 1)
"""Tuple[`int`, `int`, `int`]: The version tuple (major, minor, micro)"""


version_string = ".".join(map(str, version))
"""`str`: A version string"""


sep = sep
"""`fsnative`: Like `os.sep` but a `fsnative`"""


pathsep = pathsep
"""`fsnative`: Like `os.pathsep` but a `fsnative`"""


curdir = curdir
"""`fsnative`: Like `os.curdir` but a `fsnative`"""


pardir = pardir
"""`fsnative`: Like `os.pardir` but a fsnative"""


altsep = altsep
"""`fsnative` or `None`: Like `os.altsep` but a `fsnative` or `None`"""


extsep = extsep
"""`fsnative`: Like `os.extsep` but a `fsnative`"""


devnull = devnull
"""`fsnative`: Like `os.devnull` but a `fsnative`"""


defpath = defpath
"""`fsnative`: Like `os.defpath` but a `fsnative`"""


__all__ = []
