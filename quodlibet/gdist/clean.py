# Copyright 2007 Joe Wreschnig
#
# This software and accompanying documentation, if any, may be freely
# used, distributed, and/or modified, in any form and for any purpose,
# as long as this notice is preserved. There is no warranty, either
# express or implied, for this software.

"""clean up output of 'build' commands"""

import os

from distutils.core import Command
from distutils.command.clean import clean as distutils_clean

class clean(distutils_clean, Command):
    """clean up output of 'build' commands

    GDistribution commands generate files that the normal distutils
    clean command doesn't. This removes them.
    """

    description = "clean up output of 'build' commands"

    def initialize_options(self):
        distutils_clean.initialize_options(self)

    def finalize_options(self):
        distutils_clean.finalize_options(self)
        self.shortcuts = self.distribution.shortcuts
        self.po_package = self.distribution.po_package
        self.po_directory = self.distribution.po_directory

    def run(self):
        distutils_clean.run(self)
        if self.all:
            if self.po_directory and self.po_package:
                pot = os.path.join(self.po_directory, self.po_package + ".pot")
                try: os.unlink(pot)
                except OSError: pass

__all__ = ["clean"]
