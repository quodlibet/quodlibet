# -*- coding: utf-8 -*-
# Copyright 2017 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
Interface around faulthandler to save and restore segfault info for the
next program invocation.
"""

import os
import ctypes
import errno
import re
import atexit

import faulthandler

from quodlibet.compat import text_type
from quodlibet.util.dprint import print_exc


_fileobj = None


class FaultHandlerCrash(Exception):
    """The exception type used for raising errors with a faulthandler
    stacktrace. Needed so we can add special handling in the error reporting
    code paths.
    """

    def get_grouping_key(self):
        """Given a stacktrace produced by the faulthandler module returns a
        short string for grouping similar stacktraces together.

        Args:
            stacktrace (text_type)
        Returns:
            text_type
        """

        stacktrace = text_type(self)
        if isinstance(stacktrace, bytes):
            stacktrace = stacktrace.decode("utf-8", "replace")

        assert isinstance(stacktrace, text_type)

        # Extract the basename and the function name for each line and hash
        # them. Could be smarter, but let's try this for now..
        reg = re.compile(r'.*?"([^"]+).*?(\w+$)')
        values = []
        for l in stacktrace.splitlines():
            m = reg.match(l)
            if m is not None:
                path, func = m.groups()
                path = os.path.basename(path)
                values.extend([path, func])
        return u"|".join(values)


def enable(path):
    """Enable crash reporting and create empty target file

    Args:
        path (pathlike): the location of the crash log target path
    Raises:
        IOError: In case the location is not writable
    """

    global _fileobj

    if _fileobj is not None:
        raise Exception("already enabled")

    # we open as reading so raise_and_clear_error() can extract the old error
    try:
        _fileobj = open(path, "rb+")
    except IOError as e:
        if e.errno == errno.ENOENT:
            _fileobj = open(path, "wb+")
        else:
            raise

    faulthandler.enable(_fileobj, all_threads=False)


def disable():
    """Disable crash reporting and removes the target file

    Does not raise.
    """

    global _fileobj

    if _fileobj is None:
        return

    faulthandler.disable()

    try:
        _fileobj.close()
        os.unlink(_fileobj.name)
    except (OSError, IOError):
        pass
    _fileobj = None


@atexit.register
def _at_exit():
    disable()


def raise_and_clear_error():
    """Raises an error if there is one. Calling this will clear the error
    so a second call won't do anything.

    enable() needs to be called first.

    Raises:
        FaultHandlerCrash
    """

    global _fileobj

    if _fileobj is None:
        return

    try:
        _fileobj.seek(0)
        text = _fileobj.read().decode("utf-8", "replace").strip()
        _fileobj.seek(0)
        _fileobj.truncate()
    except IOError:
        print_exc()
    else:
        if text:
            raise FaultHandlerCrash(text)


def crash():
    """Makes the process segfault. For testing purposes"""

    if os.name == "nt":
        i = ctypes.c_char(b'a')
        j = ctypes.pointer(i)
        c = 0
        while True:
            j[c] = b'a'
            c += 1
    else:
        ctypes.string_at(0)
