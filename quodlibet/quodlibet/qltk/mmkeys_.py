# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gobject

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


def init_mmkeys(player):
    try:
        import mmkeys
    except ImportError:
        return False

    global _keys # keep a reference, or it wont work
    _keys = keys = mmkeys.MmKeys()
    signals = {"mm_prev": "prev", "mm_next": "next", "mm_stop": "stop",
               "mm_playpause": "play"}

    keys_cb = lambda p, x, a: do_action(p, a)
    for sig, action in signals.items():
        keys.connect_object(sig, keys_cb, player, action)

    return True


def init_keybinder(player):
    try:
        import keybinder
    except ImportError:
        return False

    signals = {"XF86AudioPrev": "prev", "XF86AudioNext": "next",
               "XF86AudioStop": "stop", "XF86AudioPlay": "play"}
    for sig, action in signals.items():
        keybinder.bind(sig, do_action, player, action)

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
            gobject.idle_add(do_action, player, signals[key])
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

    if init_mmkeys(player):
        print_d("mmkeys: ok")
        return

    if init_keybinder(player):
        print_d("keybinder: ok")
        return

    if init_pyhook(player):
        print_d("pyhook: ok")
        return

    print_d("grabbing failed..")
