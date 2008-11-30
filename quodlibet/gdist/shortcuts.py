# Copyright 2007 Joe Wreschnig
#
# This software and accompanying documentation, if any, may be freely
# used, distributed, and/or modified, in any form and for any purpose,
# as long as this notice is preserved. There is no warranty, either
# express or implied, for this software.

import os

from distutils.dep_util import newer
from distutils.util import change_root
from gdist.core import GCommand

class build_shortcuts(GCommand):
    """Build .desktop files

    Move .desktop files to the appropriate location in the build tree.
    If there is a .desktop.in file, process it with intltool.
    """

    description = "build .desktop files"
    user_options = []
    build_base = None

    def finalize_options(self):
        GCommand.finalize_options(self)
        self.shortcuts = self.distribution.shortcuts
        self.set_undefined_options('build', ('build_base', 'build_base'))

    def run(self):
        basepath = os.path.join(self.build_base, 'share', 'applications')
        self.mkpath(basepath)
        for shortcut in self.shortcuts:
            if os.path.exists(shortcut + ".in"):
                fullpath = os.path.join(basepath, shortcut)
                self.check_po()
                if newer(shortcut + ".in", fullpath):
                    self.spawn(["intltool-merge",
                                "-d", self.po_directory,
                                shortcut + ".in", fullpath])
            else:
                self.copy_file(shortcut, os.path.join(basepath, shortcut))

class install_shortcuts(GCommand):
    """Install .desktop files

    Install any .desktop files from the build tree to their final
    location, under $prefix/share/applications.
    """

    description = "install .desktop files"

    prefix = None
    skip_build = None
    shortcuts = None
    build_base = None
    root = None

    def finalize_options(self):
        GCommand.finalize_options(self)
        self.set_undefined_options('build', ('build_base', 'build_base'))
        self.set_undefined_options(
            'install',
            ('root', 'root'),
            ('install_base', 'prefix'),
            ('skip_build', 'skip_build'))

        self.set_undefined_options(
            'build_shortcuts', ('shortcuts', 'shortcuts'))

    def run(self):
        if not self.skip_build:
            self.run_command('build_shortcuts')
        basepath = os.path.join(self.prefix, 'share', 'applications')
        basepath = change_root(self.root, basepath)
        srcpath = os.path.join(self.build_base, 'share', 'applications')
        self.mkpath(basepath)
        for shortcut in self.shortcuts:
            fullsrc = os.path.join(srcpath, shortcut)
            fullpath = os.path.join(basepath, shortcut)
            self.copy_file(fullsrc, fullpath)

__all__ = ["build_shortcuts", "install_shortcuts"]
