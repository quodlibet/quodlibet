# -*- coding: utf-8 -*-
# Copyright 2006 Markus Koller
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import traceback
import dbus
import dbus.glib

from os.path import dirname, basename, isdir, join
from glob import glob
from ConfigParser import RawConfigParser as ConfigParser

import const
from devices._base import Device

base = dirname(__file__)
self = basename(base)
modules = [f[:-3] for f in glob(join(base, "[!_]*.py"))]
modules = ["%s.%s" % (self, basename(m)) for m in modules]

devices = []
for _name in modules:
    try: device = __import__(_name, {}, {}, self)
    except Exception, err:
        traceback.print_exc()
        continue

    try: devices.extend(device.devices)
    except AttributeError:
        print "W: %s doesn't contain any devices." % device.__name__

devices.sort()

DEVICES = os.path.join(const.USERDIR, "devices")

config = ConfigParser()
config.read(DEVICES)

def write():
    f = file(DEVICES, 'w')
    config.write(f)
    f.close()

# Return a constructor for a device given by a string
def get(name):
    try: return devices[[d.__name__ for d in devices].index(name)]
    except ValueError:
        return None

# Return a constructor for a device given by a HAL type
def get_by_type(type):
    try: return devices[[d.type for d in devices].index(type)]
    except ValueError:
        return None

# Return a new device instance for the given UDI
def get_by_udi(udi):
    interface = get_interface(udi)
    try: capabilities = interface.GetProperty('info.capabilities')
    except dbus.DBusException: return None

    if 'portable_audio_player' in capabilities:
        klass = get_by_type(interface.GetProperty('portable_audio_player.type'))
        if klass:
            device = klass(udi)
            return device
        else:
            print "W: unsupported device %s" % udi

# Return a HAL interface for the given UDI
def get_interface(udi, interface='Device'):
    interface = 'org.freedesktop.Hal.' + interface
    return dbus.Interface(
        _dbus.get_object('org.freedesktop.Hal', udi), interface)

# Discover devices with HAL
def discover():
    udis = []
    for udi in _hal.FindDeviceByCapability('portable_audio_player'):
        device = get_interface(udi)
        for vol_udi in _hal.FindDeviceStringMatch('info.parent', udi):
            volume = get_interface(vol_udi)
            if volume.GetProperty('volume.is_mounted'):
                udis.append(udi)
                break
    return udis

_dbus = dbus.SystemBus()
_hal = get_interface('/org/freedesktop/Hal/Manager', 'Manager')
