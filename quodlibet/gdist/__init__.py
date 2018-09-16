# -*- coding: utf-8 -*-
# Copyright 2007 Joe Wreschnig
#           2012-2016 Christoph Reiter
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""distutils extensions for GTK+/GObject/Unix

This module contains a Distribution subclass (GDistribution) which
implements build and install commands for operations related to
Python GTK+ and GObject support. This includes installation
of man pages and gettext support.

Also supports setuptools but needs to be imported after setuptools
(which does some monkey patching)
"""

import sys

from distutils.core import setup

from .shortcuts import build_shortcuts, install_shortcuts
from .man import install_man
from .po import build_mo, install_mo, po_stats, update_po, create_po, build_po
from .icons import install_icons
from .search_provider import install_search_provider
from .dbus_services import build_dbus_services, install_dbus_services
from .appdata import build_appdata, install_appdata
from .coverage import coverage_cmd
from .docs import build_sphinx
from .scripts import build_scripts
from .tests import quality_cmd, distcheck_cmd, test_cmd
from .clean import clean
from .zsh_completions import install_zsh_completions
from .util import get_dist_class, Distribution


distutils_build = get_dist_class("build")


class build(distutils_build):
    """Override the default build with new subcommands."""

    sub_commands = distutils_build.sub_commands + [
        ("build_mo",
         lambda self: self.distribution.has_po()),
        ("build_po",
         lambda self: self.distribution.has_po()),
        ("build_shortcuts",
         lambda self: self.distribution.has_shortcuts()),
        ("build_dbus_services",
         lambda self: self.distribution.has_dbus_services()),
        ("build_appdata",
         lambda self: self.distribution.has_appdata()),
    ]


distutils_install = get_dist_class("install")


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

    Using the translation features requires gettext.

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
        self.cmdclass.setdefault("build_po", build_po)
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
        return bool(self.po_directory)

    def has_shortcuts(self):
        return not is_osx and bool(self.shortcuts)

    def has_appdata(self):
        return not is_osx and bool(self.appdata)

    def has_man_pages(self):
        return bool(self.man_pages)

    def has_dbus_services(self):
        return not is_osx and bool(self.dbus_services)

    def has_zsh_completions(self):
        return bool(self.zsh_completions)

    def need_icon_install(self):
        return not is_osx

    def need_search_provider(self):
        return not is_osx


__all__ = ["GDistribution", "setup"]
