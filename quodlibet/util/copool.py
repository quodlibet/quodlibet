# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

"""Manager a pool of routines using Python iterators."""

import gobject

__routines = {}

def __wrap(func, funcid, args, kwargs):
    for value in func(*args, **kwargs):
        yield True
    remove(funcid)
    yield False

def add(func, *args, **kwargs):
    """Register a routine to run in GObject main loop.

    func should be a function that returns a Python iterator (e.g.
    generator) that provides values until it should stop being called.

    Optional Keyword Arguments:
    priority -- priority to run at (default PRIORITY_LOW)
    funcid -- mutex/removal identifier for this function

    Only one function with the same funcid can be running at once.
    Starting a new function with the same ID will stop the old one. If
    no funcid is given, the function itself is used. The funcid must
    be usable as a hash key.
    """
    funcid = kwargs.pop("funcid", func)
    if funcid in __routines:
        remove(funcid)
    priority = kwargs.pop("priority", gobject.PRIORITY_LOW)
    next = __wrap(func, funcid, args, kwargs).next
    __routines[funcid] = gobject.idle_add(next, priority=priority)

def remove(funcid):
    """Stop a registered routine."""
    if funcid in __routines:
        gobject.source_remove(__routines[funcid])
        del(__routines[funcid])
