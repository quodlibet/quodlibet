# -*- coding: utf-8 -*-
# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from ._base import MMKeysBackend, MMKeysAction, MMKeysImportError

import gi

try:
    gi.require_version("Keybinder", "3.0")
except ValueError:
    raise MMKeysImportError

try:
    from gi.repository import Keybinder
except ImportError:
    raise MMKeysImportError


Keybinder.init()


class KeybinderBackend(MMKeysBackend):

    _EVENTS = {
        "XF86AudioPrev": MMKeysAction.PREV,
        "XF86AudioNext": MMKeysAction.NEXT,
        "XF86AudioStop": MMKeysAction.STOP,
        "XF86AudioPlay": MMKeysAction.PLAYPAUSE,
    }

    def __init__(self, name, callback):
        self._callback = callback
        self._worked = []

        for keystring, action in self._EVENTS.items():
            if Keybinder.bind(keystring, self._bind_cb, None):
                self._worked.append(keystring)

    def _bind_cb(self, keystring, *args):
        self._callback(self._EVENTS[keystring])

    def cancel(self):
        if not self._callback:
            return
        for keystring in self._worked:
            Keybinder.unbind(keystring)
        del self._worked[:]
        self._callback = None
