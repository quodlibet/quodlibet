# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from ctypes import POINTER, Structure, cdll
from ctypes import c_longlong, c_int, c_char_p, c_void_p, c_long, c_char


c_void = None
dev_t = c_long
_classes = []


def init():
    global _classes

    udevlib = cdll.LoadLibrary("libudev.so.0")

    for info in _classes:
        _wrap_class(udevlib, *info)


def _register_class(base, ptr, prefix, methods):
    global _classes
    _classes.append((base, ptr, prefix, methods))


def _wrap_class(lib, base, ptr, prefix, methods):
    for name, ret, args in methods:
        try:
            func = getattr(lib, prefix + name)
        except AttributeError:
            # don't fail on missing ones, just in case..
            print_w("missing libudev symbol: %r" % (prefix + name))
            continue

        func.argtypes = args
        func.restype = ret

        if args and args[0] == ptr:
            add_self = lambda f: lambda *args: f(*args)
            setattr(ptr, name, add_self(func))
        else:
            setattr(base, name, func)


class Udev(Structure):
    pass


class UdevPtr(POINTER(Udev)):
    _type_ = Udev


_register_class(Udev, UdevPtr, "udev_", [
    ("ref", UdevPtr, [UdevPtr]),
    ("unref", c_void, [UdevPtr]),
    ("new", UdevPtr, []),
    #("set_log_fn", None, ...
    ("get_log_priority", c_int, [UdevPtr]),
    ("set_log_priority", c_void, [UdevPtr, c_int]),
    ("get_sys_path", c_char_p, [UdevPtr]),
    ("get_dev_path", c_char_p, [UdevPtr]),
    ("get_userdata", c_void_p, [UdevPtr]),
    ("set_userdata", c_void, [UdevPtr, c_void_p]),
])


class _UdevListIterator(object):
    def __init__(self, start_entry):
        self.__current = start_entry

    def __iter__(self):
        return self

    def next(self):
        next_ = self.__current.get_next()
        if next_:
            self.__current = next_
            return next_
        raise StopIteration


class UdevListEntry(Structure):
    pass


class UdevListEntryPtr(POINTER(UdevListEntry)):
    _type_ = UdevListEntry

    def __iter__(self):
        return _UdevListIterator(self)


_register_class(UdevListEntry, UdevListEntryPtr, "udev_list_entry_", [
    ("get_next", UdevListEntryPtr, [UdevListEntryPtr]),
    ("get_by_name", UdevListEntryPtr, [UdevListEntryPtr, c_char_p]),
    ("get_name", c_char_p, [UdevListEntryPtr]),
    ("get_value", c_char_p, [UdevListEntryPtr]),
])


class UdevDevice(Structure):
    pass


class UdevDevicePtr(POINTER(UdevDevice)):
    _type_ = UdevDevice


_register_class(UdevDevice, UdevDevicePtr, "udev_device_", [
    ("ref", UdevDevicePtr, [UdevDevicePtr]),
    ("unref", c_void, [UdevDevicePtr]),
    ("new_from_syspath", UdevDevicePtr, [UdevPtr, c_char_p]),
    ("new_from_devnum", UdevDevicePtr, [UdevPtr, c_char, dev_t]),
    ("new_from_subsystem_sysname",
     UdevDevicePtr, [UdevPtr, c_char_p, c_char_p]),
    ("get_parent", UdevDevicePtr, [UdevDevicePtr]),
    ("get_parent_with_subsystem_devtype",
     UdevDevicePtr, [UdevDevicePtr, c_char_p, c_char_p]),
    ("get_devpath", c_char_p, [UdevDevicePtr]),
    ("get_subsystem", c_char_p, [UdevDevicePtr]),
    ("get_devtype", c_char_p, [UdevDevicePtr]),
    ("get_syspath", c_char_p, [UdevDevicePtr]),
    ("get_sysname", c_char_p, [UdevDevicePtr]),
    ("get_sysnum", c_char_p, [UdevDevicePtr]),
    ("get_devnode", c_char_p, [UdevDevicePtr]),
    ("get_devlinks_list_entry", UdevListEntryPtr, [UdevDevicePtr]),
    ("get_properties_list_entry", UdevListEntryPtr, [UdevDevicePtr]),
    ("get_property_value", c_char_p, [UdevDevicePtr, c_char_p]),
    ("get_driver", c_char_p, [UdevDevicePtr]),
    ("get_devnum", dev_t, [UdevDevicePtr]),
    ("get_action", c_char_p, [UdevDevicePtr]),
    ("get_sysattr_value", c_char_p, [UdevDevicePtr, c_char_p]),
    ("get_seqnum", c_longlong, [UdevDevicePtr]),
])


class UdevMonitor(Structure):
    pass


class UdevMonitorPtr(POINTER(UdevMonitor)):
    _type_ = UdevMonitor


_register_class(UdevMonitor, UdevMonitorPtr, "udev_monitor_", [
    ("ref", UdevMonitorPtr, [UdevMonitorPtr]),
    ("unref", c_void, [UdevMonitorPtr]),
    ("get_udev", UdevPtr, [UdevMonitorPtr]),
    ("new_from_netlink", UdevMonitorPtr, [UdevPtr, c_char_p]),
    ("new_from_socket", UdevMonitorPtr, [UdevPtr, c_char_p]),
    ("enable_receiving", c_int, [UdevMonitorPtr]),
    ("get_fd", c_int, [UdevMonitorPtr]),
    ("receive_device", UdevDevicePtr, [UdevMonitorPtr]),
    ("filter_add_match_subsystem_devtype",
     c_int, [UdevMonitorPtr, c_char_p, c_char_p]),
    ("filter_update", c_int, [UdevMonitorPtr]),
    ("filter_remove", c_int, [UdevMonitorPtr]),
])


class UdevEnumerate(Structure):
    pass


class UdevEnumeratePtr(POINTER(UdevEnumerate)):
    _type_ = UdevEnumerate


_register_class(UdevEnumerate, UdevEnumeratePtr, "udev_enumerate_", [
    ("ref", UdevEnumeratePtr, [UdevEnumeratePtr]),
    ("unref", c_void, [UdevEnumeratePtr]),
    ("get_udev", UdevPtr, [UdevEnumeratePtr]),
    ("new", UdevEnumeratePtr, [UdevPtr]),
    ("add_match_subsystem", c_int, [UdevEnumeratePtr, c_char_p]),
    ("add_nomatch_subsystem", c_int, [UdevEnumeratePtr, c_char_p]),
    ("add_match_sysattr", c_int, [UdevEnumeratePtr, c_char_p, c_char_p]),
    ("add_nomatch_sysattr", c_int, [UdevEnumeratePtr, c_char_p, c_char_p]),
    ("add_match_property", c_int, [UdevEnumeratePtr, c_char_p, c_char_p]),
    ("add_match_sysname", c_int, [UdevEnumeratePtr, c_char_p]),
    ("add_syspath", c_int, [UdevEnumeratePtr, c_char_p]),
    ("scan_devices", c_int, [UdevEnumeratePtr]),
    ("scan_subsystems", c_int, [UdevEnumeratePtr]),
    ("get_list_entry", UdevListEntryPtr, [UdevEnumeratePtr]),
])


class UdevQueue(Structure):
    pass


class UdevQueuePtr(POINTER(UdevQueue)):
    _type_ = UdevQueue


_register_class(UdevQueue, UdevQueuePtr, "udev_queue_", [
    ("ref", UdevQueuePtr, [UdevQueuePtr]),
    ("unref", c_void, [UdevQueuePtr]),
    ("get_udev", UdevPtr, [UdevQueuePtr]),
    ("new", UdevQueuePtr,  [UdevPtr]),
    ("get_udev_is_active", c_int, [UdevQueuePtr]),
    ("get_queue_is_empty", c_int, [UdevQueuePtr]),
    ("get_seqnum_is_finished", c_int, [UdevQueuePtr, c_long]),
    ("get_seqnum_sequence_is_finished", c_int, [UdevQueuePtr, c_long, c_long]),
    ("get_queued_list_entry", UdevListEntryPtr, [UdevQueuePtr]),
    ("get_failed_list_entry", UdevListEntryPtr, [UdevQueuePtr]),
    ("get_kernel_seqnum", c_longlong, [UdevQueuePtr]),
    ("get_udev_seqnum", c_longlong, [UdevQueuePtr]),
])
