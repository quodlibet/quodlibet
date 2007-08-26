# Copyright 2007 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

from quodlibet.plugins import Manager

import quodlibet.qltk.playorder

class PlayOrderPlugin(quodlibet.qltk.playorder.Order):
    name = None
    display_name = None
    accelerated_name = None
    priority = quodlibet.qltk.playorder.Order.priority

class PlayOrderRememberedMixin(quodlibet.qltk.playorder.OrderRemembered):
    name = None
    display_name = None
    accelerated_name = None
    priority = quodlibet.qltk.playorder.Order.priority

class PlayOrderInOrderMixin(quodlibet.qltk.playorder.OrderInOrder):
    name = None
    display_name = None
    accelerated_name = None
    priority = quodlibet.qltk.playorder.Order.priority

class PlayOrderPlugins(Manager):
    Kinds = [PlayOrderPlugin]

    def enable(self, plugin, enabled):
        super(PlayOrderPlugins, self).enable(plugin, enabled)
        orders = self.list()
        quodlibet.qltk.playorder.set_orders(self.list())
        for plugin in self.list():
            if plugin.name is None:
                plugin.name = plugin.PLUGIN_ID
            if plugin.display_name is None:
                plugin.display_name = plugin.PLUGIN_NAME
            if plugin.accelerated_name is None:
                plugin.accelerated_name = plugin.display_name
        try:
            from quodlibet.widgets import main as window
        except ImportError: pass
        else:
            if window:
                window.order.refresh()
