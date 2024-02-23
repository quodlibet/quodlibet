# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gst

from quodlibet import _
from quodlibet.plugins.gstelement import GStreamerPlugin


class MonoDownmix(GStreamerPlugin):
    PLUGIN_ID = "mono"
    PLUGIN_NAME = _("Mono Downmix")
    PLUGIN_DESC = _("Downmixes audio channels to mono.")

    priority = -1

    @classmethod
    def setup_element(cls):
        element = Gst.ElementFactory.make("capsfilter", cls.PLUGIN_ID)
        if not element:
            return

        caps = Gst.Caps.from_string("audio/x-raw,channels=1")

        element.set_property("caps", caps)
        return element
