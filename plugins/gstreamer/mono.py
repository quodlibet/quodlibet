# -*- coding: utf-8 -*-
# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gst

from quodlibet.plugins.gstelement import GStreamerPlugin


class MonoDownmix(GStreamerPlugin):
    PLUGIN_ID = "mono"
    PLUGIN_NAME = _("Mono Downmix")
    PLUGIN_DESC = _("Downmix channels to mono.")

    priority = -1

    @classmethod
    def setup_element(cls):
        try:
            element = gst.element_factory_make('capsfilter', cls.PLUGIN_ID)
        except gst.ElementNotFoundError:
            pass
        else:
            caps_float = gst.caps_from_string('audio/x-raw-float,channels=1')
            caps_int = gst.caps_from_string('audio/x-raw-int,channels=1')
            element.set_property('caps', caps_float.union(caps_int))
            return element
