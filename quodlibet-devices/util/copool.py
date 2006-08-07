# Copyright 2006 Joe Wreschnig, Alexandre Passos
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

"""Manager a pool of routines using Python iterators."""

import gobject

__routines = {}
__paused = {}

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
    idle_id = gobject.idle_add(next, priority=priority)
    __routines[funcid] = (idle_id, next, priority)

def remove(funcid):
    """Stop a registered routine."""
    if funcid in __routines:
        gobject.source_remove(__routines[funcid][0])
        del(__routines[funcid])
    if funcid in __paused:
        del(__paused[funcid])

def pause(funcid):
    """Temporarily pause a registered routine."""
    func = __routines[funcid]
    remove(funcid)
    __paused[funcid] = func

def resume(funcid):
    """Resume a paused routine."""
    if funcid in __paused:
        old_idle_id, func, priority = __paused[funcid]
        del(__paused[funcid])
        idle_id = gobject.idle_add(func, priority=priority)
        __routines[funcid] = (idle_id, func, priority)

def step(funcid):
    """Force this function to iterate once."""
    if funcid in __routines:
        __routines[funcid][1]()
    elif funcid in self.__paused:
        __paused[funcid]()
    else:
        raise ValueError("no pooled routine %r" % funcid)
