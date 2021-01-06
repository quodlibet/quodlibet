# Copyright 2017 Christoph Reiter,
#           2017 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gst

from quodlibet.library.base import Library
from tests.plugin import PluginTestCase
from tests.helper import visible

from quodlibet.player.nullbe import NullPlayer
from quodlibet.formats import AudioFile


class FakeRMSMessage:
    type = Gst.MessageType.ELEMENT

    def __init__(self, rms_values=None):
        self.rms_values = rms_values or []

    def get_structure(self):
        class FakeStructure:

            def __init__(self, rms_values):
                self.rms_values = rms_values

            def get_name(self):
                return "level"

            def get_value(self, name):
                return self.rms_values

        return FakeStructure(self.rms_values)


class TWaveformSeekBar(PluginTestCase):

    def setUp(self):
        self.mod = self.modules["WaveformSeekBar"]

    def tearDown(self):
        del self.mod

    def test_main(self):
        WaveformScale = self.mod.WaveformScale

        player = NullPlayer()
        player.info = AudioFile({"~#length": 10})
        scale = WaveformScale(player)
        scale.compute_redraw_interval()
        scale.compute_redraw_area()

        with visible(scale):
            scale.compute_redraw_interval()
            scale.compute_redraw_area()

    def test_no_gstreamer_rms(self):
        player = NullPlayer()
        library = Library()
        bar = self.mod.WaveformSeekBar(player, library)

        message = FakeRMSMessage()
        bar._on_bus_message(None, message, 1234)
