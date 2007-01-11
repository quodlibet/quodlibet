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

from os.path import dirname, basename, join
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

_dbus = None
_hal = None

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
    return _hal.FindDeviceByCapability('portable_audio_player')

def init():
    global _dbus, _hal
    try:
        _dbus = dbus.SystemBus()
        ns = 'org.freedesktop.DBus'
        interface = dbus.Interface(
            _dbus.get_object(ns, '/org/freedesktop/DBus'), ns)
        if 'org.freedesktop.Hal' in interface.ListNames():
            _hal = get_interface('/org/freedesktop/Hal/Manager', 'Manager')
            return True
    except dbus.DBusException:
        pass
