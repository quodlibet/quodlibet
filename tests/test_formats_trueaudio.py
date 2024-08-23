# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import pytest
from tests import TestCase, get_data_path

from quodlibet.formats.trueaudio import TrueAudioFile


class TTrueAudioFile(TestCase):

    def setUp(self):
        self.song = TrueAudioFile(get_data_path("silence-44-s.tta"))

    def test_length(self):
        assert self.song("~#length") == pytest.approx(3.684, abs=1e-3)

    def test_audio_props(self):
        assert self.song("~#samplerate") == 44100

    def test_format_codec(self):
        assert self.song("~format") == "True Audio"
        assert self.song("~codec") == "True Audio"
        assert self.song("~encoding") == ""
        assert self.song("~codec") == "True Audio"
