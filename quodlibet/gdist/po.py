# Copyright 2007 Joe Wreschnig
#
# This software and accompanying documentation, if any, may be freely
# used, distributed, and/or modified, in any form and for any purpose,
# as long as this notice is preserved. There is no warranty, either
# express or implied, for this software.

"""translation support

This module contains commands to support building and installing
gettext message catalogs.
"""

import os
import glob

from distutils.dep_util import newer
from distutils.util import change_root
from gdist.core import GCommand

class build_mo(GCommand):
    """build message catalog files

    Build message catalog (.mo) files from .po files using xgettext
    and intltool.  These are placed directly in the build tree.
    """

    description = "build message catalog files"
    user_options = []
    build_base = None
    po_package = None
    po_files = None
    pot_file = None

    def finalize_options(self):
        GCommand.finalize_options(self)
        self.shortcuts = self.distribution.shortcuts
        self.po_package = self.distribution.po_package
        self.set_undefined_options('build', ('build_base', 'build_base'))
        self.po_files = glob.glob(os.path.join(self.po_directory, "*.po"))
        self.pot_file = os.path.join(
            self.po_directory, self.po_package + ".pot")

    def run(self):
        basepath = os.path.join(self.build_base, 'share', 'locale')
        infilename = os.path.join(self.po_directory, "POTFILES.in")
        infiles = file(infilename).read().splitlines()
        pot_name = os.path.join(
            self.po_directory, self.po_package + ".pot")
        for filename in infiles:
            if newer(filename, pot_name):
                oldpath = os.getcwd()
                os.chdir(self.po_directory)
                self.spawn(["intltool-update", "--pot",
                            "--gettext-package", self.po_package])
                for po in self.po_files:
                    self.spawn(["intltool-update", "--dist",
                                "--gettext-package", self.po_package,
                                os.path.basename(po[:-3])])
                os.chdir(oldpath)
        for po in self.po_files:
            language = os.path.basename(po).split(".")[0]
            fullpath = os.path.join(basepath, language, "LC_MESSAGES")
            destpath = os.path.join(fullpath, self.po_package + ".mo")
            if newer(po, destpath):
                self.mkpath(fullpath)
                self.spawn(["msgfmt", "-o", destpath, po])

class install_mo(GCommand):
    """install message catalog files

    Copy compiled message catalog files into their installation
    directory, $prefix/share/locale/$lang/LC_MESSAGES/$package.mo.
    """

    description = "install message catalog files"

    skip_build = None
    build_base = None
    install_base = None
    root = None

    def finalize_options(self):
        GCommand.finalize_options(self)
        self.set_undefined_options('build', ('build_base', 'build_base'))
        self.set_undefined_options(
            'install',
            ('root', 'root'),
            ('install_base', 'install_base'),
            ('skip_build', 'skip_build'))

    def run(self):
        if not self.skip_build:
            self.run_command('build_mo')
        src = os.path.join(self.build_base, "share", "locale")
        dest = os.path.join(self.install_base, "share", "locale")
        dest = change_root(self.root, dest)
        self.copy_tree(src, dest)

__all__ = ["build_mo", "install_mo"]
