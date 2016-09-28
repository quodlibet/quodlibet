# -*- coding: utf-8 -*-
# Copyright 2006 Markus Koller
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

from quodlibet import _
import quodlibet.devices


class Device(dict):
    """A base class for devices"""

    icon = 'multimedia-player'
    """The default icon for this device."""

    protocol = ''
    """The used HAL access method protocol for this device, as defined in
    'portable_audio_player.access_method.protocols'
    """

    udi = None
    """The UDI of this device"""

    bid = None
    """Backend device id"""

    defaults = None
    """Set this to a hash with default values for user-configurable
    properties.
    """

    def __init__(self, backend_id, device_id):
        device_manager = quodlibet.devices.device_manager
        self.udi = udi = device_id
        self.bid = bid = backend_id

        # Load default properties.
        if self.defaults:
            self.update(self.defaults)

        # Load configured properties.
        if quodlibet.devices.config.has_section(udi):
            for key in quodlibet.devices.config.options(udi):
                t = type(self.defaults.get(key))
                if t == int:
                    value = quodlibet.devices.config.getint(udi, key)
                elif t == float:
                    value = quodlibet.devices.config.getfloat(udi, key)
                elif t == bool:
                    value = quodlibet.devices.config.getboolean(udi, key)
                else:
                    value = quodlibet.devices.config.get(udi, key)
                dict.__setitem__(self, key, value)

        # Sometimes a device shows up twice. The UDI identifies the right one.
        dict.__setitem__(self, 'udi', str(udi))

        # Set a sensible name if none is set.
        if "name" not in self:
            self['name'] = device_manager.get_name(bid) or _("Unknown Device")

    def __setitem__(self, key, value):
        """Store all changed properties in the ConfigParser."""

        if not quodlibet.devices.config.has_section(self.udi):
            quodlibet.devices.config.add_section(self.udi)
        quodlibet.devices.config.set(self.udi, key, value)
        dict.__setitem__(self, key, value)

    def is_connected(self):
        """Should return True if the device is connected."""

        return os.path.ismount(self.mountpoint)

    def eject(self):
        """Eject the device, should return True on success. If the eject
        failed, it should return False or a string describing the error.
        If the device is not ejectable, set it to None.
        """

        return quodlibet.devices.device_manager.eject(self.bid)

    def get_space(self):
        """Returns a tuple with the size of this device and the free space."""

        info = os.statvfs(self.mountpoint)
        space = info.f_bsize * info.f_blocks
        free = info.f_bsize * info.f_bavail
        return (space, free)

    @property
    def mountpoint(self):
        return quodlibet.devices.device_manager.get_mountpoint(self.bid)

    @property
    def block_device(self):
        return quodlibet.devices.device_manager.get_block_device(self.bid)

    def list(self, wlb):
        """Returns a list of AudioFile instances representing the songs
        on this device. The WaitLoadBar can be used to display messages.
        """

        return []

    def contains(self, song):
        """If the device contains the passed song (it will be returned
        if list() would be called).
        """

        return False

    ordered = False
    """Whether the order of the files returned by list() is meaningful.
    If it is, refreshing will reset the song list sort order.
    """

    def copy(self, parent_widget, song):
        """ Copies a song to the device. This will be called once for each
        song. If the copy was successful, it should return an AudioFile
        instance, which will be added to the songlist. If the copy
        failed, it should return False or a string describing the error.
        """

        raise NotImplementedError

    delete = None
    """Deletes a song from the device. This will be called once for
    each song. This is not needed if the device is file-based,
    i.e. the songs returned by list() have is_file set to True. If
    the delete was successful, it should return True. If the delete
    failed, it should return False or a string describing the error.

    def delete(self, parent_widget, song): ... return True
    """

    cleanup = None
    """This will be called once after all songs have been
    copied/deleted. Should return True if no errors occured, or
    else False. The WaitLoadBar can be used to display messages.

    def cleanup(self, wlb, action='copy'|'delete'): ...
    """

    def Properties(self):
        """Returns a list of tuples for device-specific settings which
        should be displayed in the properties dialog.

        The first value should be a string and will be used as a title.
        Include an underline for changeable settings.

        The second value should be an appropriate gtk.Widget for the
        setting. It can also be a string, in which case it will be
        displayed with a Label and won't be changeable.

        The third value is the name of the object's key which should be
        set when the widget is changed. If the second value is a string,
        this will be ignored.

        Separators can be added by passing (None, None, None).
        """

        return []

    def close(self):
        pass
