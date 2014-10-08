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
# The osxmmkey plugin adds support for media keys under mac; when enabled the
# standard play, next and previous buttons control quodlibet the way you'd
# expect.
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
import sys

from quodlibet import const
from quodlibet.plugins.events import EventPlugin

if not sys.platform.startswith("darwin"):
    from quodlibet.plugins import PluginNotSupportedError
    raise PluginNotSupportedError

__all__ = ['OSXMMKey']

class OSXMMKey(EventPlugin):
    PLUGIN_ID = "OSXMMKey"
    PLUGIN_NAME = _("Mac OS X Multimedia Keys")
    PLUGIN_DESC = _("Enable Mac OS X Multimedia Shortcut Keys.\n\n"
        "Requires the PyObjC bindings (with both the Cocoa and Quartz "
        "framework bridges), and that access for assistive devices "
        "is enabled (see the Universal Access preference pane).")
    PLUGIN_VERSION = "0.1"

    __eventstap = None

    def enabled(self):
        # Start the event capturing process
        self.__eventsapp = MacKeyEventsTap()
        self.__eventsapp.runEventsCapture()

    def disabled(self):
        if self.__eventsapp is not None:
            self.__eventsapp.stopEventsCapture()
            self.__eventsapp = None


#
# Quartz event tap, listens for media key events and translates these to
# control messages for quodlibet.
#


import os
import signal
from AppKit import NSKeyUp, NSSystemDefined, NSEvent, NSApp
import Quartz

class MacKeyEventsTap(object):
    def __init__(self):
        self._keyControls = {
            16: self.play_pause,
            19: self.next,
            20: self.previous,
        }
        self._tap = None
        self._runLoopSource = None

    def eventTap(self, proxy, type_, event, refcon):
        if type_ < 0 or type_ > 0x7fffffff:
            print("E: evenTrap disabled by timeout or user input")
            return event
        # Convert the Quartz CGEvent into something more useful
        keyEvent = NSEvent.eventWithCGEvent_(event)
        if keyEvent.subtype() is 8: # subtype 8 is media keys
            data = keyEvent.data1()
            keyCode = (data & 0xFFFF0000) >> 16
            keyState = (data & 0xFF00) >> 8
            if keyCode in self._keyControls:
                if keyState == NSKeyUp:
                    self.sendControl(self._keyControls[keyCode])
                return None # swallow the event, so iTunes doesn't launch
        return event

    def sendControl(self, control):
        # invoke control directly, so we don't have to wait until 
        # the application shows to apply
        control()

    def runEventsCapture(self):
        self._tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap, # Session level is enough for our needs
            Quartz.kCGHeadInsertEventTap, # Insert wherever, we do not filter
            Quartz.kCGEventTapOptionDefault, # Active, to swallow the play/pause event is enough
            # NSSystemDefined for media keys
            Quartz.CGEventMaskBit(NSSystemDefined),
            self.eventTap,
            None
        )
        # Create a runloop source and add it to the current loop
        self._runLoopSource = Quartz.CFMachPortCreateRunLoopSource(None, self._tap, 0)
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

    def play_pause(self):
    	from quodlibet import app
        if not app.player.song:
            app.player.reset()
        else:
            app.player.paused = not app.player.paused

    def previous(self):
        from quodlibet import app
        app.player.previous()

    def next(self):
        from quodlibet import app
        app.player.next()

