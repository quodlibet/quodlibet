# Copyright 2012 Christoph Reiter
#
# This software and accompanying documentation, if any, may be freely
# used, distributed, and/or modified, in any form and for any purpose,
# as long as this notice is preserved. There is no warranty, either
# express or implied, for this software.

import os
import subprocess

from distutils.util import change_root
from distutils.core import Command


class build_icon_cache(Command):
    """Update the icon theme cache"""

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        self.spawn(['gtk-update-icon-cache', '-f', 'quodlibet/images/hicolor'])


class install_icons(Command):
    """Copy app icons to hicolor/pixmaps and update the global cache"""

    user_options = []
    root = None
    prefix = None

    def initialize_options(self):
        pass

    def finalize_options(self):
        self.set_undefined_options('install',
                                   ('root', 'root'),
                                   ('install_base', 'prefix'))

    def run(self):
        # install into hicolor icon theme
        basepath = os.path.join(self.prefix, 'share', 'icons', 'hicolor')
        if self.root is not None:
            basepath = change_root(self.root, basepath)

        local = os.path.join("quodlibet", "images", "hicolor")

        scalable = os.path.join(local, "scalable", "apps")
        scalable_dst = os.path.join(basepath, "scalable", "apps")
        self.copy_tree(scalable, scalable_dst)

        png = os.path.join(local, "64x64", "apps")
        png_dst = os.path.join(basepath, "64x64", "apps")
        self.copy_tree(png, png_dst)

        # this fails during packaging.. so ignore the outcome
        subprocess.call(['gtk-update-icon-cache', basepath])

        # install png versions to /usr/share/pixmaps
        basepath = os.path.join(self.prefix, 'share', 'pixmaps')
        if self.root is not None:
            basepath = change_root(self.root, basepath)

        self.copy_tree(png, basepath)
