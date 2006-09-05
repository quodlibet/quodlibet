# -*- coding: utf-8 -*-
# Copyright 2006 Markus Koller
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import popen2

import devices
import const
import util

class Device(dict):
    # The default icon for this device.
    icon = os.path.join(const.BASEDIR, "device-generic.png")

    # The value of the HAL-property 'portable_audio_player.type' for
    # this device.
    type = ""

    # The UDI of this device
    udi = None

    # Set this to a hash with default values for user-configurable
    # properties.
    defaults = None

    def __init__(self, udi):
        device = devices.get_interface(udi)

        self.udi = udi
        self.dev = device.GetProperty('block.device')
        self.mountpoint = ''

        # Load default properties.
        if self.defaults: self.update(self.defaults)

        # Load configured properties.
        if devices.config.has_section(udi):
            for key in devices.config.options(udi):
                t = type(self.defaults.get(key))
                if t == int:
                    value = devices.config.getint(udi, key)
                elif t == float:
                    value = devices.config.getfloat(udi, key)
                elif t == bool:
                    value = devices.config.getboolean(udi, key)
                else:
                    value = devices.config.get(udi, key)
                dict.__setitem__(self, key, value)

        # Set a sensible name if none is set.
        if not self.has_key('name'):
            # These can raise a D-Bus exception, except I'd rather
            # not have this module depend directly on D-Bus...
            try: vendor = device.GetProperty('info.vendor') + " "
            except Exception: vendor = ""
            try: name = device.GetProperty('info.product')
            except Exception: name = _("Unknown Device")
            dict.__setitem__(self, 'name', vendor + name)

    # Store all changed properties in the ConfigParser.
    def __setitem__(self, key, value):
        print "__setitem__ hook called: %s => %s" % (key, value)
        if not devices.config.has_section(self.udi):
            devices.config.add_section(self.udi)
        devices.config.set(self.udi, key, value)
        dict.__setitem__(self, key, value)

    # Should return True if the device is connected.
    def is_connected(self):
        if not self.mountpoint:
            for vol_udi in devices._hal.FindDeviceStringMatch(
                'info.parent', self.udi):
                volume = devices.get_interface(vol_udi)
                if volume.GetProperty('volume.is_mounted'):
                    self.mountpoint = str(volume.GetProperty(
                        'volume.mount_point'))
                    break
        return os.path.ismount(self.mountpoint)

    # Eject the device, should return True on success. If the eject
    # failed, it should return False or a string describing the error.
    # If the device is not ejectable, set it to None.
    def eject(self):
        if util.iscommand("eject"):
            pipe = popen2.Popen4("eject %s" % self.dev)
            if pipe.wait() == 0: return True
            else: return pipe.fromchild.read()
        else:
            return _("No eject command found.")

    # Returns a tuple with the size of this device and the free space.
    def get_space(self):
        info = os.statvfs(self.mountpoint)
        space = info.f_bsize * info.f_blocks
        free = info.f_bsize * info.f_bavail
        return (space, free)

    # Returns a list of AudioFile instances representing the songs
    # on this device. The WaitLoadBar can be used to display messages.
    def list(self, wlb): return []

    # Copies a song to the device. This will be called once for each
    # song. If the copy was successful, it should return an AudioFile
    # instance, which will be added to the songlist. If the copy
    # failed, it should return False or a string describing the error.
    def copy(self, songlist, song): raise NotImplementedError

    # Deletes a song from the device. This will be called once for
    # each song. This is not needed if the device is file-based,
    # i.e. the songs returned by list() have is_file set to True. If
    # the delete was successful, it should return True. If the delete
    # failed, it should return False or a string describing the error.
    #
    # def delete(self, songlist, song): ... return True
    delete = None

    # This will be called once after all songs have been
    # copied/deleted. Should return True if no errors occured, or
    # else False. The WaitLoadBar can be used to display messages.
    #
    # def cleanup(self, wlb, action='copy'|'delete'): ...
    cleanup = None

    # Returns a list of tuples for device-specific settings which
    # should be displayed in the properties dialog.
    #
    # The first value should be a string and will be used as a title.
    # Include an underline for changeable settings.
    #
    # The second value should be an appropriate gtk.Widget for the
    # setting. It can also be a string, in which case it will be
    # displayed with a Label and won't be changeable.
    #
    # The third value is the name of the object's key which should be
    # set when the widget is changed. If the second value is a string,
    # this will be ignored.
    #
    # Separators can be added by passing (None, None, None).
    def Properties(self): return []
