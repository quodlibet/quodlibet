# Copyright 2007 Joe Wreschnig
#
# This software and accompanying documentation, if any, may be freely
# used, distributed, and/or modified, in any form and for any purpose,
# as long as this notice is preserved. There is no warranty, either
# express or implied, for this software.

"""core support for gdist packages

This module exists to avoid circular imports within gdist.
"""

import os
import subprocess

from distutils.core import Command

class GCommand(Command):
    """An abstract base class for commands in gdist"""

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        self.po_directory = self.distribution.po_directory

    def capture(self, args):
        p = subprocess.Popen(args, stdout=subprocess.PIPE)
        ret = p.wait()
        if ret != 0:
            raise SystemExit("External program %s exited with error %d." % (args[0], ret))
        return p.stdout.read()

    def check_po(self):
        """Exit if translation is needed and not available"""
        if not (self.po_directory and os.path.isdir(self.po_directory)):
            raise SystemExit("PO directory %r not found." % self.po_directory)

__all__ = ["GCommand"]
