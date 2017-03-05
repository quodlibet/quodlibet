# -*- coding: utf-8 -*-
# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

"""
Interface around faulthandler to save and restore segfault info for the
next program invocation.
"""

import os
import ctypes
import errno

try:
    import faulthandler
except ImportError:
    faulthandler = None


_fileobj = None
_enabled = False


def enable(path):
    """Enable crash reporting and create empty target file

    Args:
        path (pathlike): the location of the crash log target path
    Raises:
        IOError: In case the location is not writable
    """

    global _fileobj, _enabled

    if _fileobj is not None:
        raise Exception("already enabled")

    _enabled = True

    if faulthandler is None:
        return

    try:
        _fileobj = open(path, "rb+")
    except IOError as e:
        if e.errno == errno.ENOENT:
            _fileobj = open(path, "wb+")

    faulthandler.enable(_fileobj)


def disable():
    """Disable crash reporting and removes the target file

    Does not raise.
    """

    global _fileobj, _enabled

    assert _enabled
    _enabled = False

    if _fileobj is None:
        return

    faulthandler.disable()

    try:
        _fileobj.close()
        os.unlink(_fileobj.name)
    except IOError:
        pass
    _fileobj = None


def check_and_clear_error():
    """Returns an error message or None. Calling this will clear the error
    so a second call will always return None.

    enable() needs to be called first.

    Returns:
        text or None
    Raises:
        IOError: In case the file couldn't be read
    """

    global _fileobj, _enabled

    assert _enabled

    if _fileobj is None:
        return

    _fileobj.seek(0)
    text = _fileobj.read().decode("utf-8", "replace").strip()
    _fileobj.seek(0)
    _fileobj.truncate()

    if text:
        return text


def crash():
    """Makes the process segfault. For testing purposes"""

    ctypes.string_at(0)
