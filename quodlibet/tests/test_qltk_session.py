# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import sys

from tests import TestCase, add

from quodlibet.qltk import session


class TSession(TestCase):
    def test_session(self):
        session.init("quodlibet")

add(TSession)
