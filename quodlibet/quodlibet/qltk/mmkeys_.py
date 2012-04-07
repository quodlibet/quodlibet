# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

class MmKeys(object):
    def __init__(self, player):
        self.__player = player
        if not self.__init_keybinder():
            self.__init_mmkeys()

    def __init_keybinder(self):
        try: import keybinder
        except: return

        signals = {"XF86AudioPrev": "prev", "XF86AudioNext": "next",
                   "XF86AudioStop": "stop", "XF86AudioPlay": "play"}
        for sig, action in signals.items():
            keybinder.bind(sig, self.__action, action)

        return True

    def __init_mmkeys(self):
        try: import mmkeys
        except: return

        self.__keys = keys = mmkeys.MmKeys()
        signals = {"mm_prev": "prev", "mm_next": "next", "mm_stop": "stop",
                   "mm_playpause": "play"}
        for sig, action in signals.items():
            keys.connect_object(sig, self.__action, action)

        return True

    def __action(self, action, *args):
        player = self.__player

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
