# Copyright 2006 Joe Wreschnig, Alexandre Passos
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

"""Manage a pool of routines using Python iterators."""

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
    timeout -- use timeout_add (with given timeout) instead of idle_add

    Only one function with the same funcid can be running at once.
    Starting a new function with the same ID will stop the old one. If
    no funcid is given, the function itself is used. The funcid must
    be usable as a hash key.
    """
    funcid = kwargs.pop("funcid", func)
    if funcid in __routines or funcid in __paused:
        remove(funcid)
    priority = kwargs.pop("priority", gobject.PRIORITY_LOW)
    timeout = kwargs.pop("timeout", None)
    next = __wrap(func, funcid, args, kwargs).next
    if timeout:
        src_id = gobject.timeout_add(timeout, next, priority=priority)
    else:
        src_id = gobject.idle_add(next, priority=priority)
    __routines[funcid] = (src_id, next, priority, timeout)
    print_d("Added copool function %r with id %r" % (func, funcid))

def remove(funcid):
    """Stop a registered routine."""
    if funcid in __routines:
        gobject.source_remove(__routines[funcid][0])
        del(__routines[funcid])
    if funcid in __paused:
        del(__paused[funcid])
    print_d("Removed copool function id %r" % funcid)

def remove_all():
    """Stop all running routines."""
    for funcid in __routines.keys():
        remove(funcid)

def pause(funcid):
    """Temporarily pause a registered routine."""
    func = __routines[funcid]
    remove(funcid)
    __paused[funcid] = func

def resume(funcid):
    """Resume a paused routine."""
    if funcid in __paused:
        old_src_id, func, priority, timeout = __paused[funcid]
        del(__paused[funcid])
        if timeout:
            src_id = gobject.timeout_add(timeout, func, priority=priority)
        else:
            src_id = gobject.idle_add(func, priority=priority)
        __routines[funcid] = (src_id, func, priority, timeout)

def step(funcid):
    """Force this function to iterate once."""
    if funcid in __routines:
        __routines[funcid][1]()
    elif funcid in __paused:
        __paused[funcid]()
    else:
        raise ValueError("no pooled routine %r" % funcid)

