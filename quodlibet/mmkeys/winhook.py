# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import ctypes

from ._base import MMKeysBackend, MMKeysAction, MMKeysImportError

try:
    from quodlibet.util import winapi
except ImportError:
    raise MMKeysImportError


class WinHookBackend(MMKeysBackend):

    def __init__(self, name, callback):
        self._callback = callback
        self._hhook = None
        self._kb_proc_ptr = None
        try:
            self._start()
        except WindowsError:
            pass

    def cancel(self):
        try:
            self._stop()
        except WindowsError:
            pass

    def _kb_proc(self, nCode, wParam, lParam):
        """A LowLevelKeyboardProc"""

        if nCode == winapi.HC_ACTION and wParam == winapi.WM_KEYDOWN:
            hstruct_ptr = ctypes.cast(lParam, winapi.LPKBDLLHOOKSTRUCT)
            assert hstruct_ptr
            hstruct = hstruct_ptr.contents
            vkCode = hstruct.vkCode

            STOP_PROCESSING = 1

            if vkCode == winapi.VK_MEDIA_PLAY_PAUSE:
                self._callback(MMKeysAction.PLAYPAUSE)
                return STOP_PROCESSING
            elif vkCode == winapi.VK_MEDIA_STOP:
                self._callback(MMKeysAction.STOP)
                return STOP_PROCESSING
            elif vkCode == winapi.VK_MEDIA_NEXT_TRACK:
                self._callback(MMKeysAction.NEXT)
                return STOP_PROCESSING
            elif vkCode == winapi.VK_MEDIA_PREV_TRACK:
                self._callback(MMKeysAction.PREV)
                return STOP_PROCESSING

        return winapi.CallNextHookEx(self._hhook, nCode, wParam, lParam)

    def _start(self):
        """Start mmkey monitoring.

        Might raise WindowsError.
        """

        kb_proc_ptr = winapi.LowLevelKeyboardProc(self._kb_proc)
        hhook = winapi.SetWindowsHookExW(
            winapi.WH_KEYBOARD_LL, kb_proc_ptr, None, 0)
        if not hhook:
            raise winapi.WinError()
        self._kb_proc_ptr = kb_proc_ptr
        self._hhook = hhook

    def _stop(self):
        """Stop mmkey monitoring. Can be called multiple times.

        Might raise WindowsError.
        """

        if self._hhook is not None:
            if winapi.UnhookWindowsHookEx(self._hhook) == 0:
                raise winapi.WinError()
            self._hhook = None
            self._kb_proc_ptr = None
