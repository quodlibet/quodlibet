# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from tests import TestCase

from quodlibet.qltk.logging import LoggingWindow


class TLoggingWindow(TestCase):
    def test_window(self):
        w = LoggingWindow()
        w.destroy()
