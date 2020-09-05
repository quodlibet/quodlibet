# Copyright 2012 Martijn Pieters <mj@zopatista.com>
# Copyright 2014 Eric Le Lay elelay.fr:dev
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
osxmmkey - Mac OS X Media Keys support
--------------------------------------

Requires the PyObjC, with the Cocoa and Quartz bindings to be installed.
Under macports, that's the `py27-pyobjc`, `py27-pyobjc-cocoa`
and`py27-pyobjc-quartz` ports, or equivalents for the python version used by
quodlibet.

This plugin also requires that 'access for assistive devices' is enabled, see
the Universal Access preference pane in the OS X System Prefences.

We register a Quartz event tap to listen for the multimedia keys and
intercept them to control QL and prevent iTunes to get them.
"""

import threading

from gi.repository import GLib

from ._base import MMKeysBackend, MMKeysAction, MMKeysImportError

try:
    from AppKit import NSKeyUp, NSSystemDefined, NSEvent
    import Quartz
except ImportError:
    raise MMKeysImportError


class OSXBackend(MMKeysBackend):

    def __init__(self, name, callback):
        self.__eventsapp = MacKeyEventsTap(callback)
        self.__eventsapp.start()

    def cancel(self):
        if self.__eventsapp is not None:
            self.__eventsapp.stop()
            self.__eventsapp = None


class MacKeyEventsTap(threading.Thread):
    # Quartz event tap, listens for media key events and translates these to
    # control messages for quodlibet.

    _EVENTS = {
        16: MMKeysAction.PLAYPAUSE,
        19: MMKeysAction.NEXT,
        20: MMKeysAction.PREV,
    }

    def __init__(self, callback):
        super(MacKeyEventsTap, self).__init__()
        self._callback = callback
        self._tap = None
        self._runLoopSource = None
        self._event = threading.Event()

    def _push_callback(self, action):
        # push to the main thread, ignore if we have been stopped by now
        def idle_call(action):
            if self._tap:
                self._callback(action)
            return False

        GLib.idle_add(idle_call, action)

    def _event_tap(self, proxy, type_, event, refcon):
        # evenTrap disabled by timeout or user input, re-enable
        if type_ == Quartz.kCGEventTapDisabledByUserInput or \
                type_ == Quartz.kCGEventTapDisabledByTimeout:
            assert self._tap is not None
            Quartz.CGEventTapEnable(self._tap, True)
            return event

        # Convert the Quartz CGEvent into something more useful
        keyEvent = NSEvent.eventWithCGEvent_(event)
        if keyEvent.subtype() == 8: # subtype 8 is media keys
            data = keyEvent.data1()
            keyCode = (data & 0xFFFF0000) >> 16
            keyState = (data & 0xFF00) >> 8
            if keyCode in self._EVENTS:
                if keyState == NSKeyUp:
                    self._push_callback(self._EVENTS[keyCode])
                return None # swallow the event, so iTunes doesn't launch
        return event

    def _loop_start(self, observer, activiti, info):
        self._event.set()

    def run(self):
        self._tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap, # Session level is enough for our needs
            Quartz.kCGHeadInsertEventTap, # Insert wherever, we do not filter
            # Active, to swallow the play/pause event is enough
            Quartz.kCGEventTapOptionDefault,
            # NSSystemDefined for media keys
            Quartz.CGEventMaskBit(NSSystemDefined),
            self._event_tap,
            None
        )

        # the above can fail
        if self._tap is None:
            self._event.set()
            return

        self._loop = Quartz.CFRunLoopGetCurrent()

        # add an observer so we know when we can stop it
        # without a race condition
        self._observ = Quartz.CFRunLoopObserverCreate(
            None, Quartz.kCFRunLoopEntry, False, 0, self._loop_start, None)
        Quartz.CFRunLoopAddObserver(
            self._loop, self._observ, Quartz.kCFRunLoopCommonModes)

        # Create a runloop source and add it to the current loop
        self._runLoopSource = Quartz.CFMachPortCreateRunLoopSource(
            None, self._tap, 0)

        Quartz.CFRunLoopAddSource(
            self._loop,
            self._runLoopSource,
            Quartz.kCFRunLoopDefaultMode
        )

        # Enable the tap
        Quartz.CGEventTapEnable(self._tap, True)

        # runrunrun
        Quartz.CFRunLoopRun()

    def stop(self):
        """Call once from the main thread to stop the thread.
        After this returns no callback will be called anymore.
        """

        # wait until we fail or the observer tells us that the loop has started
        self._event.wait()

        # failed to create a tap, nothing to stop
        if self._tap is None:
            return

        # remove the runloop source
        Quartz.CFRunLoopRemoveSource(
            self._loop,
            self._runLoopSource,
            Quartz.kCFRunLoopDefaultMode
        )
        self._runLoopSource = None

        # remove observer
        Quartz.CFRunLoopRemoveObserver(
            self._loop, self._observ, Quartz.kCFRunLoopCommonModes)
        self._observ = None

        # stop the loop
        Quartz.CFRunLoopStop(self._loop)
        self._loop = None

        # Disable the tap
        Quartz.CGEventTapEnable(self._tap, False)
        self._tap = None
