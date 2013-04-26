# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os


import gi
gi.require_version("Gio", "2.0")

from gi.repository import Gio

from quodlibet import app
from quodlibet.plugins.events import EventPlugin
from quodlibet.util.uri import URI


class AutoMasking(EventPlugin):
    PLUGIN_ID = "automask"
    PLUGIN_NAME = _("Automatic Masking")
    PLUGIN_DESC = _("Automatically mask and unmask drives when they "
                    "are unmounted or mounted, using GNOME-VFS.")
    PLUGIN_VERSION = "0.1"

    __sigs = None
    __monitor = None

    def enabled(self):
        if self.__monitor is None:
            self.__monitor = Gio.VolumeMonitor.get()
            self.__sigs = [
                self.__monitor.connect('mount-added', self.__mounted),
                self.__monitor.connect('mount-removed', self.__unmounted),
                ]
        else:
            map(self.__monitor.handler_unblock, self.__sigs)

    def disabled(self):
        map(self.__monitor.handler_block, self.__sigs)

    def __mounted(self, monitor, mount):
        path = mount.get_default_location().get_path()
        app.library.unmask(os.path.normpath(path))

    def __unmounted(self, monitor, mount):
        path = mount.get_default_location().get_path()
        app.library.mask(os.path.normpath(path))
