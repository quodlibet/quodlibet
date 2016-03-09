# -*- coding: utf-8 -*-
# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, Gdk

from quodlibet.qltk import is_wayland


def window_grab_and_map(window, mask):
    """Returns a list of devices that have a grab or an empty list if
    something failed.

    If somethings failed the window will be hidden.
    """

    device = Gtk.get_current_event_device()
    event_time = Gtk.get_current_event_time()
    if not device:
        return []

    # On wayland we need to grab before mapping and on X11 and everywhere else
    # we can grab after we are mapped
    if not is_wayland():
        window.show()
    else:
        window.realize()

    Gtk.device_grab_add(window, device, True)

    status = device.grab(
        window.get_window(), Gdk.GrabOwnership.WINDOW, True,
        mask, None, event_time)

    if status != Gdk.GrabStatus.SUCCESS:
        Gtk.device_grab_remove(window, device)
        window.hide()
        return []

    associated_device = device.get_associated_device()
    if associated_device is None:
        if is_wayland():
            window.show()
        return [device]

    Gtk.device_grab_add(window, associated_device, True)

    status = associated_device.grab(
        window.get_window(), Gdk.GrabOwnership.WINDOW, True,
        mask, None, event_time)

    if status != Gdk.GrabStatus.SUCCESS:
        Gtk.device_grab_remove(window, associated_device)
        Gtk.device_grab_remove(window, device)
        device.ungrab(event_time)
        window.hide()
        return []

    if is_wayland():
        window.show()

    return [device, associated_device]


def window_ungrab_and_unmap(window, devices):
    """Takes the result of window_grab_and_map() and removes the grabs"""

    event_time = Gtk.get_current_event_time()
    for device in devices:
        Gtk.device_grab_remove(window, device)
        device.ungrab(event_time)
    window.hide()
    #gtk3.8 bug: https://bugzilla.gnome.org/show_bug.cgi?id=700185
    window.unrealize()
