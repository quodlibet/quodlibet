# -*- coding: utf-8 -*-
# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gst

from quodlibet.plugins.gstelement import GStreamerPlugin


class MonoDownmix(GStreamerPlugin):
    PLUGIN_ID = "mono"
    PLUGIN_NAME = _("Mono Downmix")
    PLUGIN_DESC = _("Downmix channels to mono.")
    PLUGIN_ICON = "audio-volume-high"

    priority = -1

    @classmethod
    def setup_element(cls):
        element = Gst.ElementFactory.make('capsfilter', cls.PLUGIN_ID)
        if not element:
            return

        caps = Gst.Caps.from_string('audio/x-raw,channels=1')

        element.set_property('caps', caps)
        return element
