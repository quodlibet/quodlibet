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

    # The default icon for this device.
    icon = os.path.join(const.BASEDIR, "device-generic.png")

    # Set this to True if this device is writable.
    writable = False

    # Returns a list of AudioFile instances representing the songs
    # on this device. If rescan is False the list can be cached.
    def list(self, songlist, rescan=False): return []

    # Copies a song to the device. This will be called once for each song.
    # If the copy was successful, it should return an AudioFile instance,
    # which will be added to the songlist.
    # If the copy failed, it should return False or a string describing the
    # error.
    def copy(self, songlist, song): raise NotImplementedError

    # Deletes a song from the device. This will be called once for each song.
    # This is not needed if the device is file-based, i.e. the songs returned
    # by list() have is_file set to True.
    # If the delete was successful, it should return True.
    # If the delete failed, it should return False or a string describing the
    # error.
    def delete(self, songlist, song): raise NotImplementedError

    # This will be called once after all songs have been copied/deleted.
    # The WaitLoadWindow can be (ab)used to display status messages.
    # def cleanup(self, wlw, action='copy'/'delete'): ...
    cleanup = None

    # Should return True if the device is connected.
    def is_connected(self): return False

    # Eject the device, should return True on success.
    # If the device is not ejectable, set it to None.
    # def eject(self): ... return True
    eject = None

    # Returns a tuple with the size of this device and the free space.
    def get_space(self): raise NotImplementedError

    # Use dialog.add_property() to add device-specific parameters to the device
    # properties dialog. See browsers/media.py for details.
    def Properties(self, dialog): return
