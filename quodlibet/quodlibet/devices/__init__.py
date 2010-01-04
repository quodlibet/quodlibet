# -*- coding: utf-8 -*-
# Copyright 2006 Markus Koller
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import ctypes
import subprocess
import ConfigParser
from os.path import dirname, basename, join
from glob import glob

import gobject
try:
    import dbus
    import dbus.glib
except ImportError:
    dbus = None

from quodlibet import const
from quodlibet import util

base = dirname(__file__)
self = basename(base)
parent = basename(dirname(base))
modules = [f[:-3] for f in glob(join(base, "[!_]*.py"))]
modules = ["%s.%s.%s" % (parent, self, basename(m)) for m in modules]

devices = []
for _name in modules:
    try: device = __import__(_name, {}, {}, self)
    except Exception, err:
        util.print_exc()
        continue

    try: devices.extend(device.devices)
    except AttributeError:
        print_w(_("%r doesn't contain any devices.") % device.__name__)

devices.sort()

DEVICES = os.path.join(const.USERDIR, "devices")

config = ConfigParser.RawConfigParser()
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

# Return a constructor for a device given by the supported
# access method protocols
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

class DeviceManager(gobject.GObject):
    SIG_PYOBJECT = (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object,))
    __gsignals__ = {
        'removed': SIG_PYOBJECT,
        'added': SIG_PYOBJECT,
        }

    _system_bus = None

    def __init__(self, interface_name):
        super(DeviceManager, self).__init__()
        self._system_bus = dbus.SystemBus()

        ns = "org.freedesktop.DBus"
        obj = self._system_bus.get_object(ns, "/org/freedesktop/DBus")
        interface = dbus.Interface(obj, ns)

        if interface_name not in interface.ListNames():
            raise LookupError

    def discover(self):
        """Push out all existing devices"""
        raise NotImplementedError

    def get_name(self, udi):
        """A nice looking name like 'vendor' 'modelname' """
        raise NotImplementedError

    def eject(self, udi):
        """Eject device"""
        raise NotImplementedError

    def get_block_device(self, udi):
        """/dev/sdX"""
        raise NotImplementedError

    def create_device(self, backend_id, device_id, protocols):
        """backend_id is the string that gets passed to the backend so it can
        identify the device. device_id should be a something including
        the device serial (so it's unique) and maybe the model name."""
        klass = get_by_protocols(protocols)
        if klass:
            device = klass(backend_id, device_id)
            return device
        else:
            print_w(_("%r is not a supported device.") % path)

class HAL(DeviceManager):
    __interface = None

    def __init__(self):
        super(HAL, self).__init__("org.freedesktop.Hal")
        self.__interface = self.__get_interface(
            '/org/freedesktop/Hal/Manager', 'Manager')

        self.__interface.connect_to_signal('DeviceAdded', self.__device_added)
        self.__interface.connect_to_signal('DeviceRemoved',
            self.__device_removed)

    def discover(self):
        devs = self.__interface.FindDeviceByCapability('portable_audio_player')
        for udi in devs:
            device = self.__get_by_udi(udi)
            if device is not None:
                self.emit("added", device)

    def eject(self, udi):
        if util.iscommand("eject"):
            pipe = subprocess.Popen(['eject', self.get_block_device(udi)],
                    stderr=subprocess.PIPE, close_fds=True)
            if pipe.wait() == 0: return True
            else: return pipe.stderr.read()
        else:
            return _("No eject command found.")

    def get_name(self, udi):
        device = self.__get_interface(udi)
        vendor = device.GetProperty('info.vendor')
        name = device.GetProperty('info.product')
        return " ".join([vendor, name])

    def get_mountpoint(self, udi):
        udis = self.__interface.FindDeviceStringMatch('info.parent', udi)
        for vol_udi in udis:
            volume = self.__get_interface(vol_udi)
            if volume.GetProperty('volume.is_mounted'):
                return str(volume.GetProperty('volume.mount_point'))
        return ''

    def get_block_device(self, udi):
        device = self.__get_interface(udi)
        return device.GetProperty('block.device')

    def __device_added(self, udi):
        device = self.__get_by_udi(udi)
        if device is not None:
            self.emit("added", device)

    def __device_removed(self, udi):
        if device is not None:
            self.emit("removed", udi)

    def __get_by_udi(self, udi):
        """Return a new device instance for the given UDI"""
        interface = self.__get_interface(udi)
        try:
            capabilities = interface.GetProperty('info.capabilities')
        except dbus.DBusException:
            return None

        try:
            media = interface.GetProperty('storage.removable.media_available')
            if not media:
                return None
        except dbus.DBusException:
            pass

        if 'portable_audio_player' in capabilities:
            try:
                protocols = interface.GetProperty(
                    'portable_audio_player.access_method.protocols')
            except dbus.DBusException:
                try:
                    # Support older HAL versions which don't use the
                    # 'protocols' property and only store one access method
                    # as a string
                    protocols = [interface.GetProperty(
                        'portable_audio_player.access_method')]
                except dbus.DBusException:
                    return None

            #the udi is both the HAL dbus path and unique for the device
            return self.create_device(udi, basename(udi), protocols)

    def __get_interface(self, udi, interface='Device'):
        """Return a HAL interface for the given UDI"""
        interface = 'org.freedesktop.Hal.' + interface
        obj = self._system_bus.get_object('org.freedesktop.Hal', udi)
        return dbus.Interface(obj, interface)

class UdevWrapper(object):
    def __init__(self):
        self.__udev = ctypes.cdll.LoadLibrary("libudev.so.0")
        self.__struct = self.__udev.udev_new()

    def __get_attributes(self, device):
        """Pack all device attributes in a dict"""
        get_name = self.__udev.udev_list_entry_get_name
        get_value = self.__udev.udev_list_entry_get_value
        device_get_properties_list_entry = \
            self.__udev.udev_device_get_properties_list_entry
        list_entry_get_next = self.__udev.udev_list_entry_get_next

        entry = device_get_properties_list_entry(device)
        device = {}
        while entry != 0:
            name = ctypes.c_char_p(get_name(entry)).value
            value = ctypes.c_char_p(get_value(entry)).value
            device[name] = value.decode("string-escape")
            entry = list_entry_get_next(entry)
        return device

    def get_device_from_path(self, path):
        """Return the first device that matches the path"""
        path = path.encode("ascii")
        udev = self.__udev
        enumerate_scan_devices = udev.udev_enumerate_scan_devices
        device_new_from_syspath = udev.udev_device_new_from_syspath
        list_entry_get_name = udev.udev_list_entry_get_name
        enumerate_get_list_entry = udev.udev_enumerate_get_list_entry
        device_unref = udev.udev_device_unref
        enumerate_new = udev.udev_enumerate_new
        enumerate_unref = udev.udev_enumerate_unref
        enumerate_add_match_property = udev.udev_enumerate_add_match_property

        enum = enumerate_new(self.__struct)
        enumerate_add_match_property(enum, "DEVNAME", path)
        enumerate_scan_devices(enum)
        entry = enumerate_get_list_entry(enum)
        if entry != 0:
            dev = device_new_from_syspath(self.__struct,
                list_entry_get_name(entry))
            device = self.__get_attributes(dev)
            device_unref(dev)
        else:
            device = {}
        enumerate_unref(enum)

        return device

    def __del__(self):
        if self.__udev is not None:
            self.__udev.udev_unref(self.__struct)
            self.__udev = None

class DKD(DeviceManager):
    __interface = None

    def __init__(self, dkd_name):
        self.__bus = ".".join(dkd_name)
        self.__path = "/".join(dkd_name)
        super(DKD, self).__init__("org.freedesktop.%s" % self.__bus)

        interface = "org.freedesktop.%s" % self.__bus
        path = "/org/freedesktop/%s" % self.__path
        obj = self._system_bus.get_object(interface, path)
        self.__interface = dbus.Interface(obj, interface)

        self.__interface.connect_to_signal('DeviceAdded', self.__device_added)
        self.__interface.connect_to_signal('DeviceRemoved',
            self.__device_removed)

    def __get_dev_prop_interface(self, path):
        interface = "org.freedesktop.%s" % self.__bus
        obj = self._system_bus.get_object(interface, path)
        return dbus.Interface(obj, "org.freedesktop.DBus.Properties")

    def __get_dev_interface(self, path):
        interface = "org.freedesktop.%s" % self.__bus
        obj = self._system_bus.get_object(interface, path)
        return dbus.Interface(obj, "org.freedesktop.%s.Device" % self.__bus)

    def __get_dev_property(self, interface, property):
        return interface.Get("org.freedesktop.DBus.Properties", property)

    def __get_device_id(self, path):
        """A unique device id"""
        prop_if = self.__get_dev_prop_interface(path)
        vendor = self.__get_dev_property(prop_if, 'drive-vendor')
        model = self.__get_dev_property(prop_if, 'drive-model')
        serial = self.__get_dev_property(prop_if, 'drive-serial')

        return "_".join([vendor, model, serial]).replace(" ", "_")

    def __device_added(self, path):
        dev = self.__build_dev(path)
        if dev:
            self.emit("added", dev)

    def __device_removed(self, path):
        self.emit("removed", path)

    def discover(self):
        paths = self.__interface.EnumerateDevices()
        for path in paths:
            dev = self.__build_dev(path)
            if dev:
                self.emit("added", dev)

    def eject(self, path):
        prop_if = self.__get_dev_prop_interface(path)
        dev_if = self.__get_dev_interface(path)
        try:
            dev_if.FilesystemUnmount([])
            dev_if.DriveEject([])
            return True
        except dbus.DBusException:
            return False

    def get_name(self, path):
        prop_if = self.__get_dev_prop_interface(path)
        vendor = self.__get_dev_property(prop_if, 'drive-vendor')
        name = self.__get_dev_property(prop_if, 'drive-model')
        return " ".join([vendor, name])

    def get_mountpoint(self, path):
        """/media/myplayer"""
        prop_if = self.__get_dev_prop_interface(path)
        if self.__get_dev_property(prop_if, 'device-is-mounted'):
            return self.__get_dev_property(prop_if, 'device-mount-paths')[0]
        return ''

    def get_block_device(self, path):
        """/dev/sda for example"""
        prop_if = self.__get_dev_prop_interface(path)
        return self.__get_dev_property(prop_if, 'device-file')

    def __get_media_player_id(self, devpath):
        """DKD is for highlevel device stuff. The info if the device is
        a media player and what protocol/formats it supports can only
        be retrieved through libudev"""
        try: udev = UdevWrapper()
        except: return None
        dev = udev.get_device_from_path(devpath)
        try: return dev["ID_MEDIA_PLAYER"]
        except KeyError: return None

    def __get_mpi_file(self, mplayer_id):
        """Returns a SafeConfigParser instance of the mpi file or None.
        MPI files are INI like files usually located in
        /usr/local/media-player-info/*.mpi"""
        for dir in util.xdg_get_system_data_dirs():
            f = os.path.join(dir, "media-player-info", mplayer_id + ".mpi")
            if os.path.isfile(f):
                parser = ConfigParser.SafeConfigParser()
                read = parser.read(f)
                if read: return parser
        return None

    def __build_dev(self, path):
        """Return the right device instance by determining the
        supported AccessProtocol"""
        prop_if = self.__get_dev_prop_interface(path)
        #filter out useless devices
        if not self.__get_dev_property(prop_if, 'device-is-drive') or not \
            self.__get_dev_property(prop_if, 'device-is-media-available'):
            return

        #ask libudev if the device is a media player
        devpath = self.get_block_device(path)
        mplayer_id = self.__get_media_player_id(devpath)
        if mplayer_id is None: return

        #look up the supported protocols in the mpi files
        protocols = []
        config = self.__get_mpi_file(mplayer_id)
        if config is not None:
            try:
                prots = config.get("Device", "AccessProtocol")
            except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
                pass
            else:
                protocols = prots.split(";")

        device_id = self.__get_device_id(path)
        return self.create_device(path, device_id, protocols)

def init():
    global device_manager
    if not dbus: return
    device_manager = None

    print_d(_("Initializing device backend."))
    try_text = _("Trying '%s'")

    #DKD maintainers will change the naming of dbus, app stuff
    #in january 2010 or so (already changed in trunk), so try both
    """if device_manager is None:
        print_d(try_text % "DeviceKit Disks")
        try:device_manager = DKD(("DeviceKit", "Disks"))
        except (LookupError, dbus.DBusException): pass"""

    if device_manager is None:
        print_d(try_text % "UDisks")
        try: device_manager = DKD(("UDisks",))
        except (LookupError, dbus.DBusException): pass

    if device_manager is None:
        print_d(try_text % "HAL")
        try: device_manager = HAL()
        except (LookupError, dbus.DBusException): pass

    if device_manager is None:
        print_w(_("Couldn't connect to a device backend, "
            "disabling Media Devices browser."))
    else:
        print_d(_("Device backend initialized."))

    return device_manager
