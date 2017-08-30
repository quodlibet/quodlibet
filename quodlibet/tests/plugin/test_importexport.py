# -*- coding: utf-8 -*-
# Copyright 2017 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet.formats import DUMMY_SONG

from . import PluginTestCase
from ..helper import temp_filename


class TImportExport(PluginTestCase):

    def setUp(self):
        self.mod = self.modules["ExportMeta"]

    def tearDown(self):
        del self.mod

    def test_main(self):
        export_metadata = self.mod.export_metadata

        with temp_filename() as fn:
            export_metadata([DUMMY_SONG], fn)

            with open(fn) as h:
                assert h.read()
