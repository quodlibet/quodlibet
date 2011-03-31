# Copyright 2007 Joe Wreschnig
#
# This software and accompanying documentation, if any, may be freely
# used, distributed, and/or modified, in any form and for any purpose,
# as long as this notice is preserved. There is no warranty, either
# express or implied, for this software.

"""GObject extension support

This module contains commands and classes to support building
Python GObject wrappers.
"""

import os

from distutils.core import Extension
from distutils.command.build_ext import build_ext as distutils_build_ext
from gdist.core import GCommand

class GObjectExtension(Extension):
    """Generate and build GObject extensions

    This class will build GObject extensions much like the normal
    distutils Extension class builds normal CPython extensions.
    Its constructor takes two more arguments, the defs file and
    the override file.
    """
    def __init__(self, pkgname, defs, override, sources, *args, **kwargs):
        self._c_file = pkgname + "_py_codegen.c"
        self._override = override
        self._def_file = defs
        sources.append(self._c_file)
        Extension.__init__(self, pkgname, sources, *args, **kwargs)

class build_gobject_ext(distutils_build_ext, GCommand):
    """build Python GObject extensions

    This command builds Python GObject extensions by generating the
    appropriate source file with pygtk-codegen-2.0, getting the
    correct compiler flags with pkg-config, and then compiling
    everything with the default distutils extension commands.
    """

    description = "build Python GObject extensions"

    def finalize_options(self):
        distutils_build_ext.finalize_options(self)
        GCommand.finalize_options(self)
        self.extensions = self.distribution.gobject_modules
        pkg_config = ["pkg-config", "--print-errors"]
        self._defsdir = self.capture(
            pkg_config + ["--variable", "defsdir", "pygtk-2.0"]).strip()
        self._cargs = self.capture(
            pkg_config + ["--cflags", "gtk+-2.0", "pygtk-2.0"]).split()
        self._ldargs = self.capture(
            pkg_config + ["--libs", "gtk+-2.0", "pygtk-2.0"]).split()
    
    def build_extension(self, ext):
        ext.extra_compile_args.extend(self._cargs)
        ext.extra_link_args.extend(self._ldargs)
        name = ext.name.split(".")[-1]
        data = self.capture(
            ["pygtk-codegen-2.0", "--prefix", name,
             "--register", os.path.join(self._defsdir, "gdk-types.defs"),
             "--register",  os.path.join(self._defsdir, "gtk-types.defs"),
             "--override", ext._override, ext._def_file])
        fileobj = file(ext._c_file, "w")
        fileobj.write(data)
        fileobj.close()
        distutils_build_ext.build_extension(self, ext)

        os.unlink(ext._c_file)

__all__ = ["build_gobject_ext"]
