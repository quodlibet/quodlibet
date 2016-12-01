# -*- coding: utf-8 -*-
# Copyright 2016 Christoph Reiter
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

import sys
import ctypes
import collections

from ._compat import PY2
from ._fsnative import is_win, _fsn2legacy
from . import _winapi as winapi


def _get_win_argv():
    """Returns a unicode argv under Windows and standard sys.argv otherwise

    Returns:
        List[`fsnative`]
    """

    assert is_win

    argc = ctypes.c_int()
    try:
        argv = winapi.CommandLineToArgvW(
            winapi.GetCommandLineW(), ctypes.byref(argc))
    except WindowsError:
        return []

    if not argv:
        return []

    res = argv[max(0, argc.value - len(sys.argv)):argc.value]

    winapi.LocalFree(argv)

    return res


class Argv(collections.MutableSequence, list):
    """List[`fsnative`]: Like `sys.argv` but contains unicode
    keys and values under Windows + Python 2.

    Any changes made will be forwarded to `sys.argv`.
    """

    def __init__(self):
        if PY2 and is_win:
            self._argv = _get_win_argv()
        else:
            self._argv = sys.argv

    def __getitem__(self, index):
        return self._argv[index]

    def __setitem__(self, index, value):
        self._argv[index] = value
        try:
            sys.argv[index] = _fsn2legacy(value)
        except IndexError:
            pass

    def __delitem__(self, index):
        del self._argv[index]
        try:
            del sys.argv[index]
        except IndexError:
            pass

    def __len__(self):
        return len(self._argv)

    def insert(self, index, value):
        self._argv.insert(index, value)
        sys.argv.insert(index, _fsn2legacy(value))


argv = Argv()
