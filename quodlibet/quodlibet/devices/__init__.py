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
try:
    import dbus
    import dbus.glib
except ImportError:
    dbus = None

from os.path import dirname, basename, join
from glob import glob
from ConfigParser import RawConfigParser as ConfigParser

from quodlibet import const

base = dirname(__file__)
self = basename(base)
parent = basename(dirname(base))
modules = [f[:-3] for f in glob(join(base, "[!_]*.py"))]
modules = ["%s.%s.%s" % (parent, self, basename(m)) for m in modules]

devices = []
for _name in modules:
    try: device = __import__(_name, {}, {}, self)
    except Exception, err:
        traceback.print_exc()
        continue

    try: devices.extend(device.devices)
    except AttributeError:
        print_w(_("%r doesn't contain any devices.") % device.__name__)

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

# Return a constructor for a device given by the supported access method protocols
def get_by_protocols(protocols):
    # Try the storage protocol last
    if 'storage' in protocols:
        protocols.remove('storage')
        protocols.append('storage')

    for protocol in protocols:
        try: return devices[[d.protocol for d in devices].index(protocol)]
        except ValueError:
            pass

    return None

# Return a new device instance for the given UDI
def get_by_udi(udi):
    interface = get_interface(udi)
    try: capabilities = interface.GetProperty('info.capabilities')
    except dbus.DBusException: return None

    if 'portable_audio_player' in capabilities:
        klass = get_by_protocols(interface.GetProperty('portable_audio_player.access_method.protocols'))
        if klass:
            device = klass(udi)
            return device
        else:
            print_w(_("%r is not a supported device.") % udi)

# Return a HAL interface for the given UDI
def get_interface(udi, interface='Device'):
    interface = 'org.freedesktop.Hal.' + interface
    return dbus.Interface(
        _dbus.get_object('org.freedesktop.Hal', udi), interface)

# Discover devices with HAL
def discover():
    return _hal.FindDeviceByCapability('portable_audio_player')

def init():
    if not dbus:
        return
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
