# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation


from tests import TestCase

from quodlibet.qltk.quodlibetwindow import QuodLibetWindow
from quodlibet import library
from quodlibet import player
from quodlibet import config


class TQuodLibetWindow(TestCase):
    def setUp(self):
        config.init()

    def tearDown(self):
        config.quit()

    def test_window(self):
        lib = library.init()
        pl = player.init("nullbe").init(lib.librarian)
        window = QuodLibetWindow(lib, pl, headless=True)
        window.destroy()
