# Copyright 2006 Joe Wreschnig
#           2014 Christoph Reiter
#           2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

from gi.repository import Gio

from quodlibet import _
from quodlibet.qltk import Icons
from quodlibet import app
from quodlibet.plugins.events import EventPlugin


class AutoMasking(EventPlugin):
    PLUGIN_ID = "automask"
    PLUGIN_NAME = _("Automatic Masking")
    PLUGIN_DESC = _("Automatically masks and unmasks drives when they "
                    "are unmounted or mounted.")
    PLUGIN_ICON = Icons.DRIVE_REMOVABLE_MEDIA

    __sigs = None
    __monitor = None

    def enabled(self):
        if self.__monitor is None:
            self.__monitor = Gio.VolumeMonitor.get()
            self.__sigs = [
                self.__monitor.connect("mount-added", self.__mounted),
                self.__monitor.connect("mount-removed", self.__unmounted),
                ]
        else:
            for signal_id in self.__sigs:
                self.__monitor.handler_unblock(signal_id)

    def disabled(self):
        for signal_id in self.__sigs:
            self.__monitor.handler_unblock(signal_id)

    def __mounted(self, monitor, mount):
        path = mount.get_default_location().get_path()
        if path is not None:
            app.library.unmask(os.path.normpath(path))

    def __unmounted(self, monitor, mount):
        path = mount.get_default_location().get_path()
        if path is not None:
            app.library.mask(os.path.normpath(path))
