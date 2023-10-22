# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from senf import fsnative

from tests import TestCase

from quodlibet.formats.remote import RemoteFile


class TRemoteFile(TestCase):

    def test_path_types(self):
        f = RemoteFile("http://example.com")
        self.assertTrue(isinstance(f["~mountpoint"], fsnative))
        self.assertTrue(isinstance(f["~filename"], fsnative))

    def test_fix_old_types(self):
        f = RemoteFile("http://example.com")
        dict.__setitem__(f, "~filename", b"foo")
        self.assertTrue(isinstance(f["~filename"], fsnative))
        dict.__setitem__(f, "~filename", "foo")
        self.assertTrue(isinstance(f["~filename"], fsnative))
