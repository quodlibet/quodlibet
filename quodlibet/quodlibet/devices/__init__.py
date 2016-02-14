# -*- coding: utf-8 -*-
# Copyright 2006 Markus Koller
#           2012 Christoph Reiter, Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
try:
    import ConfigParser
except ImportError:
    import configparser as ConfigParser
from os.path import dirname, basename
from quodlibet.util.dprint import print_d, print_w

from gi.repository import GObject
from quodlibet.util.path import xdg_get_system_data_dirs

import quodlibet
from quodlibet import util
from quodlibet.devices import _udev as udev
from quodlibet.util.importhelper import load_dir_modules

try:
    import dbus
except ImportError:
    if not util.is_osx() and not util.is_windows():
        print_w(_("Could not import %s, which is needed for "
            "device support.") % "dbus-python")
    dbus = None


devices = []


def init_devices():
    global devices

    load_pyc = util.is_windows() or util.is_osx()
    modules = load_dir_modules(dirname(__file__),
                               package=__package__,
                               load_compiled=load_pyc)

    for mod in modules:
        try:
            devices.extend(mod.devices)
        except AttributeError:
            print_w("%r doesn't contain any devices." % mod.__name__)

    devices.sort(key=lambda d: repr(d))


if not util.is_osx() and not util.is_windows():
    init_devices()

DEVICES = os.path.join(quodlibet.get_user_dir(), "devices")

config = ConfigParser.RawConfigParser()
config.read(DEVICES)


def write():
    with open(DEVICES, 'w') as f:
        config.write(f)


# Return a constructor for a device given by a string
def get(name):
    try:
        return devices[[d.__name__ for d in devices].index(name)]
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
        try:
            return devices[[d.protocol for d in devices].index(protocol)]
        except ValueError:
            pass

    return None


class DeviceManager(GObject.GObject):
    SIG_PYOBJECT = (GObject.SignalFlags.RUN_LAST, None, (object,))
    __gsignals__ = {
        'removed': SIG_PYOBJECT,
        'added': SIG_PYOBJECT,
        }

    _system_bus = None

    def __init__(self, bus_name):
        super(DeviceManager, self).__init__()
        self._system_bus = dbus.SystemBus()

        # raises DBusException if no owner is active or can be activated
        self._system_bus.activate_name_owner(bus_name)

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

    def get_mountpoint(self, path):
        """/media/myplayer"""
        raise NotImplementedError

    def create_device(self, backend_id, device_id, protocols):
        """backend_id is the string that gets passed to the backend so it can
        identify the device. device_id should be a something including
        the device serial (so it's unique) and maybe the model name."""
        device = None

        print_d("Creating device %r supporting protocols: %r" % (
            device_id, protocols))

        for prots in (protocols, ['storage']):
            klass = get_by_protocols(prots)
            if klass is None:
                break
            try:
                device = klass(backend_id, device_id)
            except TypeError:
                pass  # rockboxed iPod
            else:
                break

        if device is None:
            print_w(_("%r is not a supported device.") % device_id)

        return device


def get_devices_from_path(udev_ctx, path):
    """A list of device attribute dicts for the given device path and all its
    parents.

    Either returns a non empty list or raises EnvironmentError.
    """

    path = path.encode("ascii")
    enum = udev.UdevEnumerate.new(udev_ctx)

    if not enum:
        raise EnvironmentError

    # only match the device we want
    if enum.add_match_property("DEVNAME", path) != 0:
        enum.unref()
        raise EnvironmentError

    # search for it
    if enum.scan_devices() != 0:
        enum.unref()
        raise EnvironmentError

    # take the first entry
    entry = enum.get_list_entry()
    if not entry:
        enum.unref()
        raise EnvironmentError
    sys_path = entry.get_name()
    enum.unref()

    device = udev.UdevDevice.new_from_syspath(udev_ctx, sys_path)
    if not device:
        raise EnvironmentError

    devices = []
    while device:
        devices.append(device)
        device = device.get_parent()

    device_attrs = []
    for device in devices:
        entry = device.get_properties_list_entry()
        if not entry:
            continue

        attrs = {}
        for e in entry:
            name = e.get_name()
            value = e.get_value()
            attrs[name] = value.decode("string-escape")
        device_attrs.append(attrs)

    # the first device owns its parents
    devices[0].unref()

    return device_attrs


def dbus_barray_to_str(array):
    return b"".join(map(bytes, array)).rstrip(b"\x00")


class UDisks2Manager(DeviceManager):

    BUS_NAME = "org.freedesktop.UDisks2"
    BLOCK_IFACE = "org.freedesktop.UDisks2.Block"
    FS_IFACE = "org.freedesktop.UDisks2.Filesystem"
    DRIVE_IFACE = "org.freedesktop.UDisks2.Drive"
    PROP_IFACE = "org.freedesktop.DBus.Properties"
    OBJMAN_IFACE = "org.freedesktop.DBus.ObjectManager"

    def __init__(self):
        super(UDisks2Manager, self).__init__(self.BUS_NAME)

        error = False

        try:
            udev.init()
        except OSError:
            print_w("UDisks2: " + _("Could not find '%s'.") % "libudev")
            error = True
        else:
            self._udev = udev.Udev.new()

        if get_mpi_dir() is None:
            print_w("UDisks2: " + _("Could not find '%s'.")
                    % "media-player-info")
            error = True

        if error:
            raise LookupError

        # object path -> properties
        self._drives = {}
        self._fs = {}
        self._blocks = {}

        # object paths -> devices (block/fs) we emitted
        self._devices = {}

        obj = self._system_bus.get_object(
            self.BUS_NAME, "/org/freedesktop/UDisks2")
        self._interface = dbus.Interface(obj, self.OBJMAN_IFACE)
        self._interface.connect_to_signal(
            'InterfacesAdded', self._interface_added)
        self._interface.connect_to_signal(
            'InterfacesRemoved', self._interface_removed)

    def _try_build_device(self, object_path, block, fs):
        """Returns a Device instance or None.

        None if it wasn't a media player etc..
        """

        drive = self._drives.get(block["Drive"])
        if not drive:
            # I think this shouldn't happen, but check anyway
            return

        dev_path = dbus_barray_to_str(block["Device"])
        print_d("Found device: %r" % dev_path)

        media_player_id = get_media_player_id(self._udev, dev_path)
        if not media_player_id:
            print_d("%r not a media player" % dev_path)
            return
        protocols = get_media_player_protocols(media_player_id)

        device_id = drive["Id"]

        dev = self.create_device(object_path, unicode(device_id), protocols)
        icon_name = block["HintIconName"]
        if icon_name:
            dev.icon = icon_name
        return dev

    def discover(self):
        objects = self._interface.GetManagedObjects()
        for object_path, interfaces_and_properties in objects.iteritems():
            self._update_interfaces(object_path, interfaces_and_properties)
        self._check_interfaces()

    def get_name(self, path):
        block = self._blocks[path]
        drive = self._drives.get(block["Drive"])
        return " - ".join([drive["Vendor"], drive["Model"]])

    def get_mountpoint(self, path):
        # the mointpoint gets filed with a delay, so fetch over dbus each time
        # the get the correct value
        obj = self._system_bus.get_object(self.BUS_NAME, path)
        interface = dbus.Interface(obj, self.PROP_IFACE)
        try:
            array = interface.Get(self.FS_IFACE, "MountPoints")
        except dbus.DBusException:
            paths = []
        else:
            paths = [dbus_barray_to_str(v) for v in array]

        if paths:
            return paths[0]
        return ""

    def get_block_device(self, path):
        block = self._blocks[path]
        return dbus_barray_to_str(block["Device"])

    def eject(self, path):
        # first try to unmount
        obj = self._system_bus.get_object(self.BUS_NAME, path)
        interface = dbus.Interface(obj, self.FS_IFACE)
        try:
            interface.Unmount({})
        except dbus.DBusException:
            pass

        # then eject..
        # XXX: this only works if no other FS is mounted..
        block = self._blocks[path]
        obj = self._system_bus.get_object(self.BUS_NAME, block["Drive"])
        interface = dbus.Interface(obj, self.DRIVE_IFACE)
        try:
            interface.Eject({})
        except dbus.DBusException:
            return False
        return True

    def _update_interfaces(self, object_path, iap):
        if self.DRIVE_IFACE in iap:
            self._drives[object_path] = iap[self.DRIVE_IFACE]
        if self.FS_IFACE in iap:
            self._fs[object_path] = iap[self.FS_IFACE]
        if self.BLOCK_IFACE in iap:
            self._blocks[object_path] = iap[self.BLOCK_IFACE]

    def _check_interfaces(self):
        # we need the block and fs interface to create a device
        for object_path in (set(self._fs.keys()) & set(self._blocks.keys())):
            # we are finished with this one, ignore
            if object_path in self._devices:
                continue
            block = self._blocks[object_path]
            fs = self._fs[object_path]
            dev = self._try_build_device(object_path, block, fs)
            if dev:
                self._devices[object_path] = dev
                self.emit("added", dev)

    def _interface_added(self, object_path, iap):
        self._update_interfaces(object_path, iap)
        self._check_interfaces()

    def _interface_removed(self, object_path, interfaces):
        if self.FS_IFACE in interfaces or self.BLOCK_IFACE in interfaces:
            # if any of our needed interfaces goes away, remove the device
            if object_path in self._devices:
                self.emit("removed", unicode(object_path))
                dev = self._devices[object_path]
                dev.close()
                del self._devices[object_path]

        if self.DRIVE_IFACE in interfaces:
            del self._drives[object_path]
        if self.FS_IFACE in interfaces:
            del self._fs[object_path]
        if self.BLOCK_IFACE in interfaces:
            del self._blocks[object_path]


def get_media_player_id(udev_ctx, dev_path):
    """Get the ID_MEDIA_PLAYER key for a specific device path e.g. /dev/sdc

    Returns the str ID or None.
    """

    try:
        devs = get_devices_from_path(udev_ctx, dev_path)
    except Exception:
        print_w("Failed to retrieve udev properties for %r" % dev_path)
        util.print_exc()
        return

    for dev in devs:
        try:
            return dev["ID_MEDIA_PLAYER"]
        except KeyError:
            continue


def get_mpi_dir():
    """Path to the media-player-info directory or None"""

    for dir_ in xdg_get_system_data_dirs():
        mpi_path = os.path.join(dir_, "media-player-info")
        if os.path.isdir(mpi_path):
            return mpi_path


def get_media_player_protocols(media_player_id):
    """Gives a list of supported protocols"""

    # get the path to the mpi files
    mpi_path = get_mpi_dir()
    if not mpi_path:
        return []

    file_path = os.path.join(mpi_path, media_player_id + ".mpi")
    parser = ConfigParser.SafeConfigParser()
    if parser.read(file_path):
        try:
            prots = parser.get("Device", "AccessProtocol")
        except ConfigParser.Error:
            return []
        else:
            return prots.split(";")
    return []


class UDisks1Manager(DeviceManager):

    def __init__(self):
        bus_name = "org.freedesktop.UDisks"
        interface = "org.freedesktop.UDisks"
        path = "/org/freedesktop/UDisks"

        super(UDisks1Manager, self).__init__(bus_name)

        error = False

        try:
            udev.init()
        except OSError:
            print_w("UDisks: " + _("Could not find '%s'.") % "libudev")
            error = True
        else:
            self.__udev = udev.Udev.new()

        if get_mpi_dir() is None:
            print_w("UDisks: " + _("Could not find '%s'.")
                    % "media-player-info")
            error = True

        if error:
            raise LookupError

        obj = self._system_bus.get_object(bus_name, path)
        self.__interface = dbus.Interface(obj, interface)

        self.__devices = {}
        self.__interface.connect_to_signal('DeviceAdded', self.__device_added)
        self.__interface.connect_to_signal('DeviceRemoved',
            self.__device_removed)

    def __get_dev_prop_interface(self, path):
        bus_name = "org.freedesktop.UDisks"
        obj = self._system_bus.get_object(bus_name, path)
        return dbus.Interface(obj, "org.freedesktop.DBus.Properties")

    def __get_dev_interface(self, path):
        bus_name = "org.freedesktop.UDisks"
        obj = self._system_bus.get_object(bus_name, path)
        return dbus.Interface(obj, "org.freedesktop.UDisks.Device")

    def __get_dev_property(self, interface, property):
        return interface.Get("org.freedesktop.DBus.Properties", property)

    def __get_device_id(self, path):
        """A unique device id"""

        prop_if = self.__get_dev_prop_interface(path)
        dev_id = self.__get_dev_property(prop_if, 'device-file-by-id')[0]
        dev_id = basename(dev_id)

        return dev_id.replace("-", "_").replace(":", "_")

    def __device_added(self, path):
        dev = self.__build_dev(path)
        if dev:
            self.__devices[path] = dev
            self.emit("added", dev)

    def __device_removed(self, path):
        # only forward removed events if we have handled the device
        if path not in self.__devices:
            return
        self.emit("removed", path)
        dev = self.__devices[path]
        dev.close()
        del self.__devices[path]

    def discover(self):
        paths = self.__interface.EnumerateDevices()
        for path in paths:
            self.__device_added(path)

    def __get_parent_disk_path(self, path):
        prop_if = self.__get_dev_prop_interface(path)
        prop_get = self.__get_dev_property
        if not prop_get(prop_if, "device-is-partition"):
            return path
        return prop_get(prop_if, "partition-slave")

    def eject(self, path):
        dev_if = self.__get_dev_interface(path)
        parent_path = self.__get_parent_disk_path(path)
        parent_if = self.__get_dev_interface(parent_path)
        try:
            dev_if.FilesystemUnmount([])
            parent_if.DriveEject([])
            return True
        except dbus.DBusException:
            return False

    def get_name(self, path):
        prop_if = self.__get_dev_prop_interface(path)
        prop_get = self.__get_dev_property

        num = ""
        if prop_get(prop_if, 'device-is-partition'):
            num = str(prop_get(prop_if, 'partition-number'))
            parent_path = prop_get(prop_if, 'partition-slave')
            prop_if = self.__get_dev_prop_interface(parent_path)

        vendor = prop_get(prop_if, 'drive-vendor')
        name = prop_get(prop_if, 'drive-model')
        return " ".join([vendor, name, num]).strip()

    def get_mountpoint(self, path):
        """/media/myplayer"""
        prop_if = self.__get_dev_prop_interface(path)
        prop_get = self.__get_dev_property
        if prop_get(prop_if, 'device-is-mounted'):
            return str(prop_get(prop_if, 'device-mount-paths')[0])
        return ''

    def get_block_device(self, path):
        """/dev/sda for example"""
        prop_if = self.__get_dev_prop_interface(path)
        return str(self.__get_dev_property(prop_if, 'device-file'))

    def __build_dev(self, path):
        """Return the right device instance by determining the
        supported AccessProtocol"""
        prop_if = self.__get_dev_prop_interface(path)
        prop_get = self.__get_dev_property

        #filter out useless devices
        if not (prop_get(prop_if, 'device-is-drive')
                or prop_get(prop_if, 'device-is-partition')) \
                or prop_get(prop_if, 'device-is-system-internal') \
                or prop_get(prop_if, 'device-is-partition-table') \
                or not prop_get(prop_if, 'device-is-media-available'):
            return

        #filter out empty partitions (issue 422)
        #http://www.win.tue.nl/~aeb/partitions/partition_types-1.html
        if prop_get(prop_if, 'device-is-partition') and \
                prop_get(prop_if, 'partition-scheme') == "mbr" and \
                int(prop_get(prop_if, 'partition-type'), 16) == 0:
            return

        # ask libudev if the device is a media player
        # and get supported protocols if any
        devpath = self.get_block_device(path)
        media_player_id = get_media_player_id(self.__udev, devpath)
        if not media_player_id:
            return
        protocols = get_media_player_protocols(media_player_id)

        # unique id
        device_id = self.__get_device_id(path)

        dev = self.create_device(path, device_id, protocols)
        icon = prop_get(prop_if, 'device-presentation-icon-name')
        if dev and icon:
            dev.icon = icon
        return dev


def init():
    global device_manager
    if not dbus:
        return
    device_manager = None

    print_d(_("Initializing device backend."))
    try_text = _("Trying '%s'")

    if device_manager is None:
        print_d(try_text % "UDisks2")
        try:
            device_manager = UDisks2Manager()
        except (LookupError, dbus.DBusException):
            pass

    if device_manager is None:
        print_d(try_text % "UDisks1")
        try:
            device_manager = UDisks1Manager()
        except (LookupError, dbus.DBusException):
            pass

    if device_manager is None:
        print_w(_("Couldn't connect to a device backend."))
    else:
        print_d(_("Device backend initialized."))

    return device_manager
