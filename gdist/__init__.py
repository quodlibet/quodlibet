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

from .shortcuts import BuildShortcuts, InstallShortcuts
from .man import InstallMan
from .po import BuildMo, InstallMo, PoStats, UpdatePo, CreatePo, CreatePot, BuildPo
from .icons import InstallIcons
from .search_provider import InstallSearchProvider
from .dbus_services import BuildDbusServices, InstallDbusServices
from .appdata import BuildAppdata, InstallAppdata
from .coverage import CoverageCmd
from .docs import BuildSphinx
from .scripts import BuildScripts
from .tests import QualityCmd, DistcheckCmd, TestCmd
from .clean import Clean
from .bash_completions import InstallBashCompletions
from .zsh_completions import InstallZshCompletions
from .util import get_dist_class, Distribution


distutils_build = get_dist_class("build")


class Build(distutils_build):
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


class Install(distutils_install):
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
        ("install_bash_completions",
         lambda self: self.distribution.has_bash_completions()),
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
    bash_completions = []
    zsh_completions = []

    def __init__(self, *args, **kwargs):
        Distribution.__init__(self, *args, **kwargs)
        self.cmdclass.setdefault("build_po", BuildPo)
        self.cmdclass.setdefault("build_mo", BuildMo)
        self.cmdclass.setdefault("build_shortcuts", BuildShortcuts)
        self.cmdclass.setdefault("build_dbus_services", BuildDbusServices)
        self.cmdclass.setdefault("build_appdata", BuildAppdata)
        self.cmdclass.setdefault("build_scripts", BuildScripts)
        self.cmdclass.setdefault("install_icons", InstallIcons)
        self.cmdclass.setdefault("install_shortcuts", InstallShortcuts)
        self.cmdclass.setdefault("install_dbus_services", InstallDbusServices)
        self.cmdclass.setdefault("install_man", InstallMan)
        self.cmdclass.setdefault("install_mo", InstallMo)
        self.cmdclass.setdefault("install_search_provider", InstallSearchProvider)
        self.cmdclass.setdefault("install_appdata", InstallAppdata)
        self.cmdclass.setdefault("install_bash_completions", InstallBashCompletions)
        self.cmdclass.setdefault("install_zsh_completions", InstallZshCompletions)
        self.cmdclass.setdefault("build", Build)
        self.cmdclass.setdefault("install", Install)
        self.cmdclass.setdefault("po_stats", PoStats)
        self.cmdclass.setdefault("update_po", UpdatePo)
        self.cmdclass.setdefault("create_po", CreatePo)
        self.cmdclass.setdefault("create_pot", CreatePot)
        self.cmdclass.setdefault("coverage", CoverageCmd)
        self.cmdclass.setdefault("build_sphinx", BuildSphinx)
        self.cmdclass.setdefault("quality", QualityCmd)
        self.cmdclass.setdefault("distcheck", DistcheckCmd)
        self.cmdclass.setdefault("test", TestCmd)
        self.cmdclass.setdefault("quality", QualityCmd)
        self.cmdclass.setdefault("clean", Clean)

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

    def has_bash_completions(self):
        return bool(self.bash_completions)

    def has_zsh_completions(self):
        return bool(self.zsh_completions)

    def need_icon_install(self):
        return not is_osx

    def need_search_provider(self):
        return not is_osx


__all__ = ["GDistribution", "setup"]
