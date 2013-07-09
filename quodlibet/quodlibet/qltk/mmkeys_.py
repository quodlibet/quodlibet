# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import GLib

__all__ = ["init"]


def do_action(player, action):
    print_d("action: %s" % action)

    if action == "prev":
        player.previous()
    elif action == "next":
        player.next()
    elif action == "stop":
        player.stop()
    elif action == "play":
        if player.song is None:
            player.reset()
        else:
            player.paused ^= True
    elif action == "pause":
        player.paused = True
    else:
        print_d("didn't handle: %s" % action)


def init_dbus_mmkeys(window, player):
    try:
        from quodlibet.qltk.dbusmmkey import DBusMMKey
    except ImportError: # no dbus
        return False

    if not DBusMMKey.is_active():
        return False

    sigs = {"Next": "next", "Previous": "prev", "Play": "play",
            "Pause": "pause", "Next": "next", "Stop": "stop"}

    keys = DBusMMKey(window, "quodlibet")
    keys.connect_object("action", lambda p, a: do_action(p, sigs[a]), player)

    return True


def make_keybinder_cb(player, action):
    return lambda keystring, user_data: do_action(player, action)


def init_keybinder(player):
    try:
        import gi
        gi.require_version("Keybinder", "3.0")
        from gi.repository import Keybinder
    except (ValueError, ImportError):
        return False

    Keybinder.init()

    signals = {"XF86AudioPrev": "prev", "XF86AudioNext": "next",
               "XF86AudioStop": "stop", "XF86AudioPlay": "play"}
    for sig, action in signals.items():
        Keybinder.bind(sig, make_keybinder_cb(player, action), None)

    return True


def init_pyhook(player):
    try:
        import pyHook
    except ImportError:
        return False

    signals = {"Media_Prev_Track": "prev", "Media_Next_Track": "next",
               "Media_Stop": "stop", "Media_Play_Pause": "play"}

    def keyboard_cb(event):
        key = event.Key
        if key in signals:
            GLib.idle_add(do_action, player, signals[key])
        return True

    hm = pyHook.HookManager()
    hm.KeyDown = keyboard_cb
    hm.HookKeyboard()

    return True


def init(window, player):
    print_d("Grab multimedia keys")

    if init_dbus_mmkeys(window, player):
        print_d("dbus mmkeys: ok")
        return

    if init_keybinder(player):
        print_d("keybinder: ok")
        return

    if init_pyhook(player):
        print_d("pyhook: ok")
        return

    print_d("grabbing failed..")
