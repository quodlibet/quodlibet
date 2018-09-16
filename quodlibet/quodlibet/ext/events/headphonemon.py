# -*- coding: utf-8 -*-
# Copyright 2015 Christoph Reiter
#           2017 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import sys

from quodlibet.qltk import Icons

if os.name == "nt" or sys.platform == "darwin":
    from quodlibet.plugins import PluginNotSupportedError
    raise PluginNotSupportedError

import fcntl
import subprocess

from gi.repository import GLib, GObject

from quodlibet import _
from quodlibet.plugins.events import EventPlugin
from quodlibet.util import print_d
from quodlibet import app


def get_headphone_status():
    """Returns if headphones are connected."""

    # No idea if this is a good way... but works here :)
    try:
        data = subprocess.check_output(["pactl", "list", "sinks"])
    except OSError:
        return False
    for line in data.splitlines():
        if line.strip() == b"Active Port: analog-output-headphones":
            return True
    else:
        return False


class HeadphoneAction(object):
    DISCONNECTED = 0
    CONNECTED = 1


class HeadphoneMonitor(GObject.Object):
    """Monitors the headphone connection state advertised by pulseaudio.

    After start() is called will emit a signal in case headphones
    get connected or disconnected.

    If pulseaudio isn't active this will work but always return
    a disconnected status.

    The changed signal will never be emitted with the same status multiple
    times.
    """

    __gsignals__ = {
        'action': (GObject.SignalFlags.RUN_LAST, None, (object,)),
    }

    def __init__(self):
        super(HeadphoneMonitor, self).__init__()
        self._subscribe_id = None
        self._process = None
        self._status = None

    def is_connected(self):
        """Returns whether headphones are currently connected"""

        if self._status is None:
            raise Exception("call start() first")

        return self._status

    def _emit(self):
        self.emit("action",
                  HeadphoneAction.CONNECTED if self._status else
                    HeadphoneAction.DISCONNECTED)

    def _update_status(self):
        assert self._status is not None
        new_status = get_headphone_status()
        if new_status != self._status:
            self._status = new_status
            self._emit()
            return

    def start(self):
        """Start the monitoring process.

        Once this gets called the "changed" signal will be emitted.
        """

        NULL = open(os.devnull, 'wb')
        try:
            self._process = subprocess.Popen(
                ["pactl", "subscribe"], stdout=subprocess.PIPE, stderr=NULL)
        except OSError:
            self._status = False
            return

        f = self._process.stdout
        fcntl.fcntl(f, fcntl.F_SETFL, os.O_NONBLOCK)

        def can_read_cb(fd, flags):
            if flags & (GLib.IOCondition.HUP | GLib.IOCondition.ERR):
                f.close()
                self._subscribe_id = None
                return False

            data = f.read()
            if not data:
                f.close()
                self._subscribe_id = None
                return False

            # querying the status also results in client events which would
            # lead us into an endless loop. Instead just something if there
            # is a sink event
            if b" on sink " in data:
                self._update_status()
            return True

        self._status = get_headphone_status()
        self._subscribe_id = GLib.io_add_watch(
            f, GLib.PRIORITY_HIGH,
            GLib.IOCondition.IN | GLib.IOCondition.ERR | GLib.IOCondition.HUP,
            can_read_cb)

    def stop(self):
        """Stop the monitoring process.

        After this returns no signal will be emitted.
        Can be called multiple times.
        start() can be called to start monitoring again after this returns.
        """

        if self._subscribe_id is not None:
            GLib.source_remove(self._subscribe_id)
            self._subscribe_id = None

        if self._process is not None:
            self._process.terminate()
            self._process.wait()
            self._process = None

        self._status = None


class HeadphoneMonitorPlugin(EventPlugin):
    PLUGIN_ID = "HeadphoneMonitor"
    PLUGIN_NAME = _("Pause on Headphone Unplug")
    PLUGIN_DESC = _("Pauses in case headphones get unplugged and unpauses in "
                    "case they get plugged in again.")
    PLUGIN_ICON = Icons.MEDIA_PLAYBACK_PAUSE

    def enabled(self):
        self._was_paused = False
        self._do_act = False
        self._mon = HeadphoneMonitor()
        self._mon.connect("action", self._changed)
        self._mon.start()

    def _changed(self, mon, action):
        if action == HeadphoneAction.DISCONNECTED:
            print_d("Headphones disconnected")
            if self._do_act:
                do_act = self._do_act
                self._was_paused = app.player.paused
                app.player.paused = True
                self._do_act = do_act
        elif action == HeadphoneAction.CONNECTED:
            print_d("Headphones connected")
            if self._do_act:
                do_act = self._do_act
                app.player.paused = self._was_paused
                self._do_act = do_act

    def disabled(self):
        self._mon.stop()
        del self._mon

    def plugin_on_paused(self):
        self._do_act = False

    def plugin_on_unpaused(self):
        self._do_act = self._mon.is_connected()
