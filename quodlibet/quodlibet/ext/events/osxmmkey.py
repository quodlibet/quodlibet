# -*- coding: utf-8 -*-
# Copyright 2012 Martijn Pieters <mj@zopatista.com>
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
# We run a separate process (not a fork!) so we can run a Quartz event loop
# without having to bother with making that work with the GTK event loop.
# There we register a Quartz event tap to listen for the multimedia keys and
# control QL through it's const.CONTROL pipe.

import subprocess
import sys
try:
    from quodlibet import const
    from quodlibet.plugins.events import EventPlugin

    if not sys.platform.startswith("darwin"):
        from quodlibet.plugins import PluginNotSupportedError
        raise PluginNotSupportedError

except ImportError:
    # When executing the event tap process, we may not be able to import
    # quodlibet libraries, which is fine.
    pass
else:
    __all__ = ['OSXMMKey']

    class OSXMMKey(EventPlugin):
        PLUGIN_ID = "OSXMMKey"
        PLUGIN_NAME = _("Mac OS X Multimedia Keys")
        PLUGIN_DESC = _("Enable Mac OS X Multimedia Shortcut Keys.\n\n"
            "Requires the PyObjC bindings (with both the Cocoa and Quartz "
            "framework bridges), and that access for assistive devices "
            "is enabled (see the Universal Access preference pane).")
        PLUGIN_VERSION = "0.1"

        __eventsapp = None

        def enabled(self):
            # Start the event capturing process
            self.__eventsapp = subprocess.Popen(
                (sys.executable, __file__, const.CONTROL))

        def disabled(self):
            if self.__eventsapp is not None:
                self.__eventsapp.kill()
                self.__eventsapp = None


#
# Quartz event tap, listens for media key events and translates these to
# control messages for quodlibet.
#


import os
import signal
from AppKit import NSKeyUp, NSSystemDefined, NSEvent
import Quartz


class MacKeyEventsTap(object):
    def __init__(self, controlPath):
        self._keyControls = {
            16: 'play-pause',
            19: 'next',
            20: 'previous',
        }
        self.controlPath = controlPath

    def eventTap(self, proxy, type_, event, refcon):
        # Convert the Quartz CGEvent into something more useful
        keyEvent = NSEvent.eventWithCGEvent_(event)
        if keyEvent.subtype() is 8: # subtype 8 is media keys
            data = keyEvent.data1()
            keyCode = (data & 0xFFFF0000) >> 16
            keyState = (data & 0xFF00) >> 8
            if keyState == NSKeyUp and keyCode in self._keyControls:
                self.sendControl(self._keyControls[keyCode])

    def sendControl(self, control):
        # Send our control message to QL.
        if not os.path.exists(self.controlPath):
            sys.exit()
        try:
            # This is a total abuse of Python! Hooray!
            # Totally copied from the quodlibet command line handler too..
            signal.signal(signal.SIGALRM, lambda: "" + 2)
            signal.alarm(1)
            f = file(self.controlPath, "w")
            signal.signal(signal.SIGALRM, signal.SIG_IGN)
            f.write(control)
            f.close()
        except (OSError, IOError, TypeError):
            sys.exit()

    @classmethod
    def runEventsCapture(cls, controlPath):
        tapHandler = cls(controlPath)
        tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap, # Session level is enough for our needs
            Quartz.kCGHeadInsertEventTap, # Insert wherever, we do not filter
            Quartz.kCGEventTapOptionListenOnly, # Listening is enough
            # NSSystemDefined for media keys
            Quartz.CGEventMaskBit(NSSystemDefined),
            tapHandler.eventTap,
            None
        )
        # Create a runloop source and add it to the current loop
        runLoopSource = Quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
        Quartz.CFRunLoopAddSource(
            Quartz.CFRunLoopGetCurrent(),
            runLoopSource,
            Quartz.kCFRunLoopDefaultMode
        )
        # Enable the tap
        Quartz.CGEventTapEnable(tap, True)
        # and run! This won't return until we exit or are terminated.
        Quartz.CFRunLoopRun()


if __name__ == '__main__':
    # In the subprocess, capture media key events
    MacKeyEventsTap.runEventsCapture(sys.argv[1])
