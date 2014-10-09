# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import pyHook
from gi.repository import GLib

from ._base import MMKeysBackend, MMKeysAction


class PyHookBackend(MMKeysBackend):

    _EVENTS = {
        "Media_Prev_Track": MMKeysAction.PREV,
        "Media_Next_Track": MMKeysAction.NEXT,
        "Media_Stop": MMKeysAction.STOP,
        "Media_Play_Pause": MMKeysAction.PLAYPAUSE,
    }

    def __init__(self, name, callback):
        self._hm = pyHook.HookManager()
        self._hm.KeyDown = self._keyboard_cb
        self._callback = callback
        self._hm.HookKeyboard()

    def _keyboard_cb(self, event):

        def idle_cb(action):
            if not self._callback:
                return

            self._callback(action)
            return False

        key = event.Key
        if key in self._EVENTS:
            GLib.idle_add(idle_cb, self._EVENTS[key])

        # True, pass to other handlers
        return True

    def cancel(self):
        if not self._hm:
            return
        self._hm.UnhookKeyboard()
        self._hm.KeyDown = None
        self._hm = None
        self._callback = None
