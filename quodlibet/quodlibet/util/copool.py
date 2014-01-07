# Copyright 2006 Joe Wreschnig, Alexandre Passos
#           2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

"""Manage a pool of routines using Python iterators."""

from gi.repository import GLib


class _Routine(object):

    def __init__(self, pool, func, funcid, priority, timeout, args, kwargs):
        self.priority = priority
        self.timeout = timeout
        self._source_id = None

        def wrap(func, funcid, args, kwargs):
            for value in func(*args, **kwargs):
                yield True
            pool.remove(funcid)
            yield False

        self.source_func = wrap(func, funcid, args, kwargs).next

    @property
    def paused(self):
        """If the routine is currently running"""

        return self._source_id is None

    def step(self):
        """Raises StopIteration if the routine has nothing more to do"""

        return self.source_func()

    def resume(self):
        """Resume, if already running do nothing"""

        if not self.paused:
            return

        if self.timeout:
            self._source_id = GLib.timeout_add(
                self.timeout, self.source_func, priority=self.priority)
        else:
            self._source_id = GLib.idle_add(
                self.source_func, priority=self.priority)

    def pause(self):
        """Pause, if already paused, do nothing"""

        if self.paused:
            return

        GLib.source_remove(self._source_id)
        self._source_id = None


class CoPool(object):

    def __init__(self):
        self.__routines = {}

    def add(self, func, *args, **kwargs):
        """Register a routine to run in GLib main loop.

        func should be a function that returns a Python iterator (e.g.
        generator) that provides values until it should stop being called.

        Optional Keyword Arguments:
        priority -- priority to run at (default GLib.PRIORITY_LOW)
        funcid -- mutex/removal identifier for this function
        timeout -- use timeout_add (with given timeout) instead of idle_add
                   (in milliseconds)

        Only one function with the same funcid can be running at once.
        Starting a new function with the same ID will stop the old one. If
        no funcid is given, the function itself is used. The funcid must
        be usable as a hash key.
        """

        funcid = kwargs.pop("funcid", func)
        if funcid in self.__routines:
            remove(funcid)

        priority = kwargs.pop("priority", GLib.PRIORITY_LOW)
        timeout = kwargs.pop("timeout", None)

        print_d("Added copool function %r with id %r" % (func, funcid))
        routine = _Routine(self, func, funcid, priority, timeout, args, kwargs)
        self.__routines[funcid] = routine
        routine.resume()

    def _get(self, funcid):
        if funcid in self.__routines:
            return self.__routines[funcid]
        raise ValueError("no pooled routine %r" % funcid)

    def remove(self, funcid):
        """Stop a registered routine."""

        routine = self._get(funcid)
        routine.pause()
        del self.__routines[funcid]
        print_d("Removed copool function id %r" % funcid)

    def remove_all(self):
        """Stop all running routines."""

        for funcid in self.__routines.keys():
            self.remove(funcid)

    def pause(self, funcid):
        """Temporarily pause a registered routine."""

        routine = self._get(funcid)
        routine.pause()
        print_d("Paused copool function id %r" % funcid)

    def resume(self, funcid):
        """Resume a paused routine."""

        routine = self._get(funcid)
        routine.resume()
        print_d("Resumed copool function id %r" % funcid)

    def step(self, funcid):
        """Force this function to iterate once."""

        routine = self._get(funcid)
        return routine.step()


# global instance

_copool = CoPool()

add = _copool.add
pause = _copool.pause
remove = _copool.remove
remove_all = _copool.remove_all
resume = _copool.resume
step = _copool.step
