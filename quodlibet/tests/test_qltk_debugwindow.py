# -*- coding: utf-8 -*-
# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import sys

from tests import TestCase
from .helper import capture_output

from quodlibet.qltk.debugwindow import ExceptionDialog, MinExceptionDialog


class TExceptionDialog(TestCase):
    def test_exec_hook(self):
        with capture_output():
            try:
                raise Exception
            except Exception:
                ExceptionDialog.from_except(*sys.exc_info())
                ExceptionDialog.instance.destroy()


class TMinExceptionDialog(TestCase):

    def test_main(self):
        MinExceptionDialog(None, u"foo", u"bar", u"quux\nquux2").destroy()
