# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase

from quodlibet.qltk.msg import WarningMessage, ErrorMessage, \
    CancelRevertSave, ConfirmFileReplace


class TWarningMessage(TestCase):

    def test_ctr(self):
        WarningMessage(None, "title", "description").destroy()


class TErrorMessage(TestCase):

    def test_ctr(self):
        ErrorMessage(None, "title", "description").destroy()


class TCancelRevertSave(TestCase):
    def setUp(self):
        self.win = CancelRevertSave(None)

    def test_ctr(self):
        pass

    def tearDown(self):
        self.win.destroy()


class TFileReplace(TestCase):

    def setUp(self):
        self.win = ConfirmFileReplace(None, "")

    def test_ctr(self):
        pass

    def tearDown(self):
        self.win.destroy()
