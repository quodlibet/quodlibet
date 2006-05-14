# -*- coding: utf-8 -*-
# Copyright 2006 Markus Koller
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os

import const

class Device(object):
    # The default name used for new devices of this type.
    name = ""

    # A description for this device.
    description = ""

    # The default icon that will be displayed when this device is selected.
    icon = os.path.join(const.BASEDIR, "device-generic.png")

    # Set this to True if this device is writable.
    writable = False

    # Returns a list of AudioFile instances representing the songs
    # on this device. If rescan is False the list can be cached.
    def list(self, browser, rescan=False): return []

    # Takes one or more songs and copies it to the device.
    def copy(self, songs): raise NotImplementedError

    # Deletes one or more songs from the device.
    def delete(self, songs): raise NotImplementedError

    # Should return True if the device is connected.
    def is_connected(self): return False

    # Set this to True if this device is ejectable.
    # You'll also need to provide an eject() method.
    ejectable = False

    # Returns True if the eject was successful, or else a string
    # with an error message.
    def eject(self): raise NotImplementedError

    # Returns a formatted string with information about this device.
    def get_info(self): raise NotImplementedError

    # Returns a tuple with the size of this device and the free space.
    def get_space(self): raise NotImplementedError

    # Use dialog.add_property() to add device-specific parameters.
    # See browsers/media.py for details.
    def Properties(self, dialog): return
