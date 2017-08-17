# -*- coding: utf-8 -*-
# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

"""Everything related to Ubuntu Unity integration (quicklist..)

See the MPRIS plugin for sound menu integration.
"""

import gi

from quodlibet import _
from quodlibet.util import gi_require_versions


is_unity = True
try:
    gi.require_version("Dbusmenu", "0.4")
    from gi.repository import Dbusmenu
except (ValueError, ImportError):
    is_unity = False

try:
    gi_require_versions("Unity", ["7.0", "6.0", "5.0"])
    from gi.repository import Unity
except (ValueError, ImportError):
    is_unity = False


def init(desktop_id, player):
    """Set up unity integration.

    * desktop_id: e.g. 'quodlibet.desktop'
    * player: BasePlayer()

    http://developer.ubuntu.com/api/devel/ubuntu-12.04/c/Unity-5.0.html
    http://developer.ubuntu.com/api/devel/ubuntu-13.10/c/Unity-7.0.html
    """

    if not is_unity:
        return

    launcher = Unity.LauncherEntry.get_for_desktop_id(desktop_id)

    main = Dbusmenu.Menuitem()

    play_pause = Dbusmenu.Menuitem()
    play_pause.property_set(Dbusmenu.MENUITEM_PROP_LABEL,
                            _("Play/Pause"))
    play_pause.property_set_bool(Dbusmenu.MENUITEM_PROP_VISIBLE, True)
    main.child_append(play_pause)

    def play_pause_cb(item, timestamp):
        player.playpause()

    play_pause.connect("item-activated", play_pause_cb)

    next_ = Dbusmenu.Menuitem()
    next_.property_set(Dbusmenu.MENUITEM_PROP_LABEL, _("Next"))
    next_.property_set_bool(Dbusmenu.MENUITEM_PROP_VISIBLE, True)
    main.child_append(next_)

    def next_cb(item, timestamp):
        player.next()

    next_.connect("item-activated", next_cb)

    prev = Dbusmenu.Menuitem()
    prev.property_set(Dbusmenu.MENUITEM_PROP_LABEL, _("Previous"))
    prev.property_set_bool(Dbusmenu.MENUITEM_PROP_VISIBLE, True)
    main.child_append(prev)

    def prev_cb(item, timestamp):
        player.previous()

    prev.connect("item-activated", prev_cb)

    launcher.set_property("quicklist", main)
