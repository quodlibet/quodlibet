# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gtk

import config

_ORDERS = ["inorder", "shuffle", "weighted", "onesong"]
_TRANS = {"inorder": _("In Order"),
          "shuffle": _("Shuffle"),
          "weighted": _("Weighted"),
          "onesong": _("One Song")
          }

class PlayOrder(gtk.ComboBox):
    def __init__(self, model):
        super(PlayOrder, self).__init__(gtk.ListStore(str))
        cell = gtk.CellRendererText()
        self.pack_start(cell, True)
        self.add_attribute(cell, 'text', 0)
        for order in _ORDERS: self.append_text(_TRANS[order])
        self.connect_object('changed', self.__changed_order, model)
        self.set_active(config.get("memory", "order"))

    def set_active(self, value):
        try: super(PlayOrder, self).set_active(_ORDERS.index(value))
        except: super(PlayOrder, self).set_active(int(value))

    def get_active_name(self):
        return _ORDERS[self.get_active()]

    def __changed_order(self, model):
        model.order = self.get_active()
        config.set("memory", "order", _ORDERS[self.get_active()])

