# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from collections.abc import Sequence

from gi.repository import Gtk, Gdk, GObject

from quodlibet.qltk import is_wayland


GSignals = dict[str, tuple[GObject.SignalFlags, type | None, Sequence[type]] | str]


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
        window.get_window(), Gdk.GrabOwnership.WINDOW, True, mask, None, event_time
    )

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
        window.get_window(), Gdk.GrabOwnership.WINDOW, True, mask, None, event_time
    )

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
    # gtk3.8 bug: https://bugzilla.gnome.org/show_bug.cgi?id=700185
    window.unrealize()


def position_window_beside_widget(window, widget, end=True, pad=3):
    """Positions `window` left or right beside `widget` on the screen.
    `padding` is the space between the widget and the window.
    If `end` is True the window will be placed on the right side
    in LTR mode or on the left side in RTL mode.
    """

    if Gtk.Widget.get_default_direction() != Gtk.TextDirection.LTR:
        right = not end
    else:
        right = end

    assert widget.get_realized()

    toplevel = widget.get_toplevel()
    dx, dy = widget.translate_coordinates(toplevel, 0, 0)
    x, y = toplevel.get_window().get_origin()[1:]
    x += dx
    y += dy

    widget_alloc = widget.get_allocation()
    w, h = widget_alloc.width, widget_alloc.height

    window.size_request()
    ww, wh = window.get_size()

    if right:
        sx, sy = ((x + w + pad), (y + (h - wh) // 2))
    else:
        sx, sy = ((x - (ww + pad)), (y + (h - wh) // 2))

    window.move(sx, sy)
