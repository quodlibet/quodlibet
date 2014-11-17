# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from tests import TestCase

from quodlibet.util.path import is_fsnative
from quodlibet.formats.remote import RemoteFile


class TRemoteFile(TestCase):

    def test_path_types(self):
        f = RemoteFile("http://example.com")
        self.assertTrue(is_fsnative(f["~mountpoint"]))
        self.assertTrue(is_fsnative(f["~filename"]))

    def test_fix_old_types(self):
        f = RemoteFile("http://example.com")
        f["~filename"] = b"foo"
        self.assertTrue(is_fsnative(f["~filename"]))
        f["~filename"] = u"foo"
        self.assertTrue(is_fsnative(f["~filename"]))
