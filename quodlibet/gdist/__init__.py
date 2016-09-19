# -*- coding: utf-8 -*-
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
import sys

try:
    from py2exe import Distribution
except ImportError:
    from distutils.core import Distribution

from distutils.command.build import build as distutils_build
from distutils.command.install import install as distutils_install

from gdist.shortcuts import build_shortcuts, install_shortcuts
from gdist.man import install_man
from gdist.po import build_mo, install_mo, po_stats, update_po, create_po
from gdist.icons import install_icons
from gdist.search_provider import install_search_provider
from gdist.dbus_services import build_dbus_services, install_dbus_services
from gdist.appdata import build_appdata, install_appdata
from gdist.coverage import coverage_cmd
from gdist.docs import build_sphinx
from gdist.scripts import build_scripts
from gdist.tests import quality_cmd, distcheck_cmd, test_cmd
from gdist.clean import clean
from gdist.zsh_completions import install_zsh_completions


class build(distutils_build):
    """Override the default build with new subcommands."""

    user_options = distutils_build.user_options + [
        ("skip-po-update", None, "Don't update pot/po files"),
    ]

    sub_commands = distutils_build.sub_commands + [
        ("build_mo",
         lambda self: self.distribution.has_po()),
        ("build_shortcuts",
         lambda self: self.distribution.has_shortcuts()),
        ("build_dbus_services",
         lambda self: self.distribution.has_dbus_services()),
        ("build_appdata",
         lambda self: self.distribution.has_appdata()),
    ]


class install(distutils_install):
    """Override the default install with new subcommands."""

    user_options = distutils_install.user_options + [
        ("mandir=", None, "destination directory for man pages. "
                          "Defaults to $PREFIX/share/man"),
    ]

    sub_commands = distutils_install.sub_commands + [
        ("install_shortcuts", lambda self: self.distribution.has_shortcuts()),
        ("install_man", lambda self: self.distribution.has_man_pages()),
        ("install_mo", lambda self: self.distribution.has_po()),
        ("install_icons", lambda self: self.distribution.need_icon_install()),
        ("install_search_provider",
         lambda self: self.distribution.need_search_provider()),
        ("install_dbus_services",
         lambda self: self.distribution.has_dbus_services()),
        ("install_appdata",
         lambda self: self.distribution.has_appdata()),
        ("install_zsh_completions",
         lambda self: self.distribution.has_zsh_completions()),
    ]

    def initialize_options(self):
        distutils_install.initialize_options(self)
        self.mandir = None


is_windows = (os.name == "nt")
is_osx = (sys.platform == "darwin")


class GDistribution(Distribution):
    """A Distribution with support for GTK+-related options

    The GDistribution class adds a number of commads and parameters
    related to GTK+ and GObject Python programs and libraries.

    Parameters (to distutils.core.setup):
      po_directory -- directory where .po files are contained
      po_package -- package name for translation files
      shortcuts -- list of .desktop files to build/install
      dbus_services -- list of .service files to build/install
      man_pages -- list of man pages to install
      appdata -- list of appdata files to install

    Using the translation features requires intltool.

    Example:
      from distutils.core import setup
      from gdist import GDistribution

      setup(distclass=GDistribution, ...)
      """

    shortcuts = []
    appdata = []
    dbus_services = []
    po_directory = None
    man_pages = []
    po_package = None
    search_provider = None
    coverage_options = {}
    zsh_completions = []

    def __init__(self, *args, **kwargs):
        Distribution.__init__(self, *args, **kwargs)
        self.cmdclass.setdefault("build_mo", build_mo)
        self.cmdclass.setdefault("build_shortcuts", build_shortcuts)
        self.cmdclass.setdefault("build_dbus_services", build_dbus_services)
        self.cmdclass.setdefault("build_appdata", build_appdata)
        self.cmdclass.setdefault("build_scripts", build_scripts)
        self.cmdclass.setdefault("install_icons", install_icons)
        self.cmdclass.setdefault("install_shortcuts", install_shortcuts)
        self.cmdclass.setdefault("install_dbus_services",
                                 install_dbus_services)
        self.cmdclass.setdefault("install_man", install_man)
        self.cmdclass.setdefault("install_mo", install_mo)
        self.cmdclass.setdefault("install_search_provider",
                                 install_search_provider)
        self.cmdclass.setdefault("install_appdata", install_appdata)
        self.cmdclass.setdefault(
            "install_zsh_completions", install_zsh_completions)
        self.cmdclass.setdefault("build", build)
        self.cmdclass.setdefault("install", install)
        self.cmdclass.setdefault("po_stats", po_stats)
        self.cmdclass.setdefault("update_po", update_po)
        self.cmdclass.setdefault("create_po", create_po)
        self.cmdclass.setdefault("coverage", coverage_cmd)
        self.cmdclass.setdefault("build_sphinx", build_sphinx)
        self.cmdclass.setdefault("quality", quality_cmd)
        self.cmdclass.setdefault("distcheck", distcheck_cmd)
        self.cmdclass.setdefault("test", test_cmd)
        self.cmdclass.setdefault("quality", quality_cmd)
        self.cmdclass.setdefault("clean", clean)

    def has_po(self):
        return not is_windows and bool(self.po_directory)

    def has_shortcuts(self):
        return not is_windows and not is_osx and bool(self.shortcuts)

    def has_appdata(self):
        return not is_windows and not is_osx and bool(self.appdata)

    def has_man_pages(self):
        return not is_windows and bool(self.man_pages)

    def has_dbus_services(self):
        return not is_windows and not is_osx and bool(self.dbus_services)

    def has_zsh_completions(self):
        return not is_windows and bool(self.zsh_completions)

    def need_icon_install(self):
        return not is_windows and not is_osx

    def need_search_provider(self):
        return not is_windows and not is_osx

__all__ = ["GDistribution"]
