# Copyright 2013-2016 Christoph Reiter
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

"""
AppData Specification: https://www.freedesktop.org/software/appstream/docs/
"""

import os

from distutils.dep_util import newer
from .util import Command
from .gettextutil import merge_file


class BuildAppdata(Command):
    """Build .appdata.xml files

    Move .appdata.xml files to the appropriate location in the build tree.
    If there is a .appdata.xml.in file, process it with gettext.
    """

    description = "build .appdata.xml files"
    user_options = []

    def initialize_options(self):
        self.build_base = None
        self.appdata = None
        self.po_build_dir = None

    def finalize_options(self):
        self.appdata = self.distribution.appdata
        self.set_undefined_options("build", ("build_base", "build_base"))
        self.set_undefined_options("build_po", ("po_build_dir", "po_build_dir"))

    def run(self):
        self.run_command("build_po")

        basepath = os.path.join(self.build_base, "share", "metainfo")
        self.mkpath(basepath)
        for appdata in self.appdata:
            if os.path.exists(appdata + ".in"):
                fullpath = os.path.join(basepath, os.path.basename(appdata))
                if newer(appdata + ".in", fullpath):
                    merge_file(self.po_build_dir, "xml", appdata + ".in", fullpath)
            else:
                self.copy_file(appdata, os.path.join(basepath, appdata))


class InstallAppdata(Command):
    """Install .appdata.xml files

    Install any .appdata.xml files from the build tree to their final
    location, under $prefix/share/metainfo.
    """

    description = "install .appdata.xml files"
    user_options = []

    def initialize_options(self):
        self.install_dir = None
        self.skip_build = None
        self.appdata = None
        self.build_base = None
        self.outfiles = []

    def finalize_options(self):
        self.set_undefined_options("build", ("build_base", "build_base"))
        self.set_undefined_options(
            "install", ("install_data", "install_dir"), ("skip_build", "skip_build")
        )

        self.set_undefined_options("build_appdata", ("appdata", "appdata"))

    def get_outputs(self):
        return self.outfiles

    def run(self):
        if not self.skip_build:
            self.run_command("build_appdata")

        basepath = os.path.join(self.install_dir, "share", "metainfo")
        srcpath = os.path.join(self.build_base, "share", "metainfo")
        out = self.mkpath(basepath)
        self.outfiles.extend(out or [])
        for appdata in self.appdata:
            appdata = os.path.basename(appdata)
            fullsrc = os.path.join(srcpath, appdata)
            fullpath = os.path.join(basepath, appdata)
            (out, _) = self.copy_file(fullsrc, fullpath)
            self.outfiles.append(out)


__all__ = ["BuildAppdata", "InstallAppdata"]
