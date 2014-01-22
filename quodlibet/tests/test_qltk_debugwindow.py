# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import sys

from tests import TestCase

from quodlibet.qltk.debugwindow import ExceptionDialog


class TExceptionDialog(TestCase):
    def test_exec_hook(self):
        old = sys.stderr
        try:
            sys.stderr = None
            try:
                raise Exception
            except Exception:
                ExceptionDialog.from_except(*sys.exc_info())
                ExceptionDialog.instance.destroy()
        finally:
            sys.stderr = old
