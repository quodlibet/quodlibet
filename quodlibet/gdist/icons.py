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


def update_icon_cache(*args):
    args = list(args)
    try:
        subprocess.check_call(
            ['gtk-update-icon-cache-3.0'] + args)
    except OSError:
        try:
            subprocess.check_call(
                ['gtk-update-icon-cache'] + args)
        except OSError:
            return False
        except subprocess.CalledProcessError:
            return False
    except subprocess.CalledProcessError:
        return False
    return True


class build_icon_cache(Command):
    """Update the icon theme cache"""

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        if not update_icon_cache('-f', 'quodlibet/images/hicolor'):
            print "WARNING: gtk-update-icon-cache missing"


class install_icons(Command):
    """Copy app icons to hicolor/pixmaps and update the global cache"""

    user_options = []
    root = None
    prefix = None

    def initialize_options(self):
        self.outfiles = []

    def finalize_options(self):
        self.set_undefined_options('install',
                                   ('root', 'root'),
                                   ('install_base', 'prefix'))

    def get_outputs(self):
        return self.outfiles

    def run(self):
        # install into hicolor icon theme
        basepath = os.path.join(self.prefix, 'share', 'icons', 'hicolor')
        if self.root is not None:
            basepath = change_root(self.root, basepath)

        local = os.path.join("quodlibet", "images", "hicolor")

        scalable = os.path.join(local, "scalable", "apps")
        scalable_dst = os.path.join(basepath, "scalable", "apps")
        out = self.copy_tree(scalable, scalable_dst)
        self.outfiles.extend(out)

        png = os.path.join(local, "64x64", "apps")
        png_dst = os.path.join(basepath, "64x64", "apps")
        out = self.copy_tree(png, png_dst)
        self.outfiles.extend(out)

        # this fails during packaging.. so ignore the outcome
        update_icon_cache(basepath)

        # install png versions to /usr/share/pixmaps
        basepath = os.path.join(self.prefix, 'share', 'pixmaps')
        if self.root is not None:
            basepath = change_root(self.root, basepath)

        out = self.copy_tree(png, basepath)
        self.outfiles.extend(out)
