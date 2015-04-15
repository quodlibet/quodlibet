# -*- coding: utf-8 -*-
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

from distutils.core import Command


class install_man(Command):
    """install man pages

    Install man pages into $prefix/share/man/manN
    or into $mandir/manN by using setup.py install --mandir=$mandir
    """

    description = "install man pages"
    user_options = []

    def initialize_options(self):
        self.man_pages = None
        self.mandir = None
        self.install_dir = None
        self.outfiles = []

    def finalize_options(self):
        self.set_undefined_options(
            'install',
            ('install_data', 'install_dir'),
            ('mandir', 'mandir'),
        )

        if self.mandir is None:
            self.mandir = os.path.join(self.install_dir, 'share', 'man')

        self.man_pages = self.distribution.man_pages
        for man_page in self.man_pages:
            if not man_page[-1].isdigit():
                raise SystemExit("%r has no section" % man_page)

    def get_outputs(self):
        return self.outfiles

    def run(self):
        basepath = self.mandir
        out = self.mkpath(basepath)
        self.outfiles.extend(out or [])

        for man_page in self.man_pages:
            manpath = os.path.join(basepath, "man" + man_page[-1])
            out = self.mkpath(manpath)
            self.outfiles.extend(out or [])
            fullpath = os.path.join(manpath, os.path.basename(man_page))
            (out, _) = self.copy_file(man_page, fullpath)
            self.outfiles.append(out)

__all__ = ["install_man"]
