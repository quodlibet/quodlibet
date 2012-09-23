# Copyright 2007 Joe Wreschnig
#
# This software and accompanying documentation, if any, may be freely
# used, distributed, and/or modified, in any form and for any purpose,
# as long as this notice is preserved. There is no warranty, either
# express or implied, for this software.

"""install man pages

Commands to install Unix man pages.
"""

import os

from distutils.util import change_root
from distutils.core import Command

class install_man(Command):
    """install man pages

    Install man pages into $prefix/share/man/manN.
    """

    description = "install man pages"
    user_options = []

    man_pages = None
    prefix = None
    root = None

    def initialize_options(self):
        pass

    def finalize_options(self):
        self.set_undefined_options('install', ('root', 'root'), ('install_base', 'prefix'))
        self.man_pages = self.distribution.man_pages
        for man_page in self.man_pages:
            if not man_page[-1].isdigit():
                raise SystemExit("%r has no section" % man_page)

    def run(self):
        basepath = os.path.join(self.prefix, 'share', 'man')
        if self.root != None:
          basepath = change_root(self.root, basepath)
        self.mkpath(basepath)
        for man_page in self.man_pages:
            manpath = os.path.join(basepath, "man" + man_page[-1])
            self.mkpath(manpath)
            fullpath = os.path.join(manpath, os.path.basename(man_page))
            self.copy_file(man_page, fullpath)

__all__ = ["install_man"]
