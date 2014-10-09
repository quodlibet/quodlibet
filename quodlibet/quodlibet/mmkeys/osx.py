# -*- coding: utf-8 -*-
# Copyright 2012 Martijn Pieters <mj@zopatista.com>
# Copyright 2014 Eric Le Lay elelay.fr:dev
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# osxmmkey - Mac OS X Media Keys support
# --------------------------------------
#
# Requires the PyObjC, with the Cocoa and Quartz bindings to be installed.
# Under macports, that's the `py27-pyobjc`, `py27-pyobjc-cocoa`
# and`py27-pyobjc-quartz` ports, or equivalents for the python version used by
# quodlibet.
#
# This plugin also requires that 'access for assistive devices' is enabled, see
# the Universal Access preference pane in the OS X System Prefences.
#
# We register a Quartz event tap to listen for the multimedia keys and
# intercept them to control QL and prevent iTunes to get them.


from AppKit import NSKeyUp, NSSystemDefined, NSEvent
import Quartz

from ._base import MMKeysBackend, MMKeysAction


class OSXBackend(MMKeysBackend):

    def __init__(self, name, callback):
        self.__eventsapp = MacKeyEventsTap(callback)
        self.__eventsapp.runEventsCapture()

    def cancel(self):
        if self.__eventsapp is not None:
            self.__eventsapp.stopEventsCapture()
            self.__eventsapp = None


class MacKeyEventsTap(object):
    # Quartz event tap, listens for media key events and translates these to
    # control messages for quodlibet.

    _EVENTS = {
        16: MMKeysAction.PLAYPAUSE,
        19: MMKeysAction.NEXT,
        20: MMKeysAction.PREVIOUS,
    }

    def __init__(self, callback):
        self._tap = None
        self._runLoopSource = None
        self._callback = callback

    def _eventTap(self, proxy, type_, event, refcon):
        if type_ < 0 or type_ > 0x7fffffff:
            print_w("evenTrap disabled by timeout or user input")
            Quartz.CGEventTapEnable(self._tap, True)
            return event

        # Convert the Quartz CGEvent into something more useful
        keyEvent = NSEvent.eventWithCGEvent_(event)
        if keyEvent.subtype() is 8: # subtype 8 is media keys
            data = keyEvent.data1()
            keyCode = (data & 0xFFFF0000) >> 16
            keyState = (data & 0xFF00) >> 8
            if keyCode in self._EVENTS:
                if keyState == NSKeyUp:
                    self._callback(self._EVENTS[keyCode])
                return None # swallow the event, so iTunes doesn't launch
        return event

    def runEventsCapture(self):
        self._tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap, # Session level is enough for our needs
            Quartz.kCGHeadInsertEventTap, # Insert wherever, we do not filter
            # Active, to swallow the play/pause event is enough
            Quartz.kCGEventTapOptionDefault,
            # NSSystemDefined for media keys
            Quartz.CGEventMaskBit(NSSystemDefined),
            self._eventTap,
            None
        )

        # Create a runloop source and add it to the current loop
        self._runLoopSource = Quartz.CFMachPortCreateRunLoopSource(
            None, self._tap, 0)
        Quartz.CFRunLoopAddSource(
            Quartz.CFRunLoopGetMain(),
            self._runLoopSource,
            Quartz.kCFRunLoopDefaultMode
        )

        # Enable the tap
        Quartz.CGEventTapEnable(self._tap, True)

    def stopEventsCapture(self):
        # Disable the tap
        Quartz.CGEventTapEnable(self._tap, False)
        self._tap = None

        # remove the runloop source
        Quartz.CFRunLoopRemoveSource(
            Quartz.CFRunLoopGetMain(),
            self._runLoopSource,
            Quartz.kCFRunLoopDefaultMode
        )
        self._runLoopSource = None
