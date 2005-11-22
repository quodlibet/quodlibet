# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gtk

import config
import stock
from qltk.sliderbutton import VSlider

class Volume(VSlider):
    def __init__(self, device):
        i = gtk.image_new_from_stock(
            stock.VOLUME_MAX, gtk.ICON_SIZE_LARGE_TOOLBAR)
        super(type(self), self).__init__(i)
        self.scale.set_update_policy(gtk.UPDATE_CONTINUOUS)
        self.scale.set_inverted(True)
        self.get_value = self.scale.get_value
        self.scale.connect('value-changed', self.__volume_changed, device, i)
        self.set_value(config.getfloat("memory", "volume"))
        self.__volume_changed(self.scale, device, i)
        self.show_all()

    def set_value(self, v):
        self.scale.set_value(max(0.0, min(1.0, v)))

    def __iadd__(self, v):
        self.set_value(min(1.0, self.get_value() + v))
        return self
    def __isub__(self, v):
        self.set_value(max(0.0, self.get_value() - v))
        return self

    def __volume_changed(self, slider, device, image):
        val = slider.get_value()
        if val == 0: img = stock.VOLUME_OFF
        elif val < 0.33: img = stock.VOLUME_MIN
        elif val < 0.66: img = stock.VOLUME_MED
        else: img = stock.VOLUME_MAX
        image.set_from_stock(img, gtk.ICON_SIZE_LARGE_TOOLBAR)

        device.volume = val
        config.set("memory", "volume", str(slider.get_value()))
