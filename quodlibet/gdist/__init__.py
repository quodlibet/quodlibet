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

from distutils.core import Distribution
from distutils.command.build import build as distutils_build
from distutils.command.install import install as distutils_install

from gdist.gobject import build_gobject_ext, GObjectExtension
from gdist.shortcuts import build_shortcuts, install_shortcuts
from gdist.man import install_man
from gdist.po import build_mo, install_mo

class build(distutils_build):
    """Override the default build with new subcommands."""
    sub_commands = distutils_build.sub_commands + [
        ("build_mo",
         lambda self: self.distribution.has_po()),
        ("build_shortcuts",
         lambda self: self.distribution.has_shortcuts()),
        ("build_gobject_ext",
         lambda self: self.distribution.has_gobject_ext()),
        ]

class install(distutils_install):
    """Override the default install with new subcommands."""

    sub_commands = distutils_install.sub_commands + [
        ("install_shortcuts", lambda self: self.distribution.has_shortcuts()), 
        ("install_man", lambda self: self.distribution.has_man_pages()),
        ("install_mo", lambda self: self.distribution.has_po()),
       ]

class GDistribution(Distribution):
    """A Distribution with support for GTK+-related options

    The GDistribution class adds a number of commads and parameters
    related to GTK+ and GObject Python programs and libraries.

    Parameters (to distutils.core.setup):
      po_directory -- directory where .po files are contained
      po_package -- package name for translation files
      shortcuts -- list of .desktop files to build/install
      gobject_modules -- list of GObjectExtensions to build
      man_pages -- list of man pages to install

    Using the translation features requires intltool.
    Using GObjectExtensions requires pygtk-codegen-2.0.

    Example:
      from distutils.core import setup
      from gdist import GDistribution
      
      setup(distclass=GDistribution, ...)
      """

    gobject_modules = []
    shortcuts = []
    po_directory = None
    man_pages = []
    po_package = None

    def __init__(self, *args, **kwargs):
        Distribution.__init__(self, *args, **kwargs)
        self.cmdclass.setdefault("build_gobject_ext", build_gobject_ext)
        self.cmdclass.setdefault("build_mo", build_mo)
        self.cmdclass.setdefault("build_shortcuts", build_shortcuts)
        self.cmdclass.setdefault("install_shortcuts", install_shortcuts)
        self.cmdclass.setdefault("install_man", install_man)
        self.cmdclass.setdefault("install_mo", install_mo)
        self.cmdclass.setdefault("build", build)
        self.cmdclass.setdefault("install", install)

    def has_po(self):
        return bool(self.po_directory)

    def has_shortcuts(self):
        return bool(self.shortcuts)

    def has_gobject_ext(self):
        return bool(self.gobject_modules)

    def has_man_pages(self):
        return bool(self.man_pages)

__all__ = ["GDistribution", "GObjectExtension"]
