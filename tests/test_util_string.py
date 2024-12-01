# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase

from quodlibet.util.string import isascii


class Tisascii(TestCase):

    def test_main(self):
        assert isascii("")
        assert isascii("")
        assert isascii("abc")
        assert isascii("abc")
        assert not isascii("\xffbc")
        assert not isascii("übc")
