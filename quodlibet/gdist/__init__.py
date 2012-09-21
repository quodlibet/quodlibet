# Copyright 2007 Joe Wreschnig
#
# This software and accompanying documentation, if any, may be freely
# used, distributed, and/or modified, in any form and for any purpose,
# as long as this notice is preserved. There is no warranty, either
# express or implied, for this software.

"""distutils extensions for GTK+/GObject/Unix

This module contains a Distribution subclass (GDistribution) which
implements build and install commands for operations related to
Python GTK+ and GObject support. This includes installation
of man pages and gettext/intltool support.
"""

import os

try:
    from py2exe import Distribution
except ImportError:
    from distutils.core import Distribution

from distutils.command.build import build as distutils_build
from distutils.command.install import install as distutils_install

from gdist.shortcuts import build_shortcuts, install_shortcuts
from gdist.man import install_man
from gdist.po import build_mo, install_mo, po_stats, check_pot
from gdist.icons import build_icon_cache, install_icons


class build(distutils_build):
    """Override the default build with new subcommands."""
    sub_commands = distutils_build.sub_commands + [
        ("build_mo",
         lambda self: self.distribution.has_po()),
        ("build_shortcuts",
         lambda self: self.distribution.has_shortcuts()),
        ("build_icon_cache",
         lambda self: self.distribution.need_icon_cache()),
        ]

class install(distutils_install):
    """Override the default install with new subcommands."""

    sub_commands = distutils_install.sub_commands + [
        ("install_shortcuts", lambda self: self.distribution.has_shortcuts()),
        ("install_man", lambda self: self.distribution.has_man_pages()),
        ("install_mo", lambda self: self.distribution.has_po()),
        ("install_icons", lambda self: self.distribution.need_icon_install()),
       ]

class GDistribution(Distribution):
    """A Distribution with support for GTK+-related options

    The GDistribution class adds a number of commads and parameters
    related to GTK+ and GObject Python programs and libraries.

    Parameters (to distutils.core.setup):
      po_directory -- directory where .po files are contained
      po_package -- package name for translation files
      shortcuts -- list of .desktop files to build/install
      man_pages -- list of man pages to install

    Using the translation features requires intltool.

    Example:
      from distutils.core import setup
      from gdist import GDistribution

      setup(distclass=GDistribution, ...)
      """

    shortcuts = []
    po_directory = None
    man_pages = []
    po_package = None

    def __init__(self, *args, **kwargs):
        Distribution.__init__(self, *args, **kwargs)
        self.cmdclass.setdefault("build_mo", build_mo)
        self.cmdclass.setdefault("build_shortcuts", build_shortcuts)
        self.cmdclass.setdefault("build_icon_cache", build_icon_cache)
        self.cmdclass.setdefault("install_icons", install_icons)
        self.cmdclass.setdefault("install_shortcuts", install_shortcuts)
        self.cmdclass.setdefault("install_man", install_man)
        self.cmdclass.setdefault("install_mo", install_mo)
        self.cmdclass.setdefault("build", build)
        self.cmdclass.setdefault("install", install)
        self.cmdclass.setdefault("po_stats", po_stats)
        self.cmdclass.setdefault("check_pot", check_pot)

    def has_po(self):
        return os.name != 'nt' and bool(self.po_directory)

    def has_shortcuts(self):
        return os.name != 'nt' and bool(self.shortcuts)

    def has_man_pages(self):
        return os.name != 'nt' and bool(self.man_pages)

    def need_icon_cache(self):
        return os.name != 'nt'

    def need_icon_install(self):
        return os.name != 'nt'

__all__ = ["GDistribution"]
