# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gnomevfs

import library

from plugins.events import EventPlugin
from util.uri import URI

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
            self.__monitor = gnomevfs.VolumeMonitor()
            self.__sigs = [
                self.__monitor.connect('volume-mounted', self.__mounted),
                self.__monitor.connect('volume-unmounted', self.__unmounted),
                ]
        else:
            map(self.__monitor.handler_unblock, self.__sigs)

    def disabled(self):
        map(self.__monitor.handler_block, self.__sigs)

    def __mounted(self, monitor, volume):
        try: filename = URI(volume.get_activation_uri()).filename
        except ValueError: pass
        else: library.library.unmask(os.path.normpath(filename))

    def __unmounted(self, monitor, volume):
        try: filename = URI(volume.get_activation_uri()).filename
        except ValueError: pass
        else: library.library.mask(os.path.normpath(filename))
