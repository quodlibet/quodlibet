# Copyright 2007 Joe Wreschnig
#           2012,2013,2015, 2016 Christoph Reiter
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

"""clean up output of 'build' commands"""

import os
import shutil

from .util import get_dist_class


distutils_clean = get_dist_class("clean")


class Clean(distutils_clean):
    """clean up output of 'build' commands

    GDistribution commands generate files that the normal distutils
    clean command doesn't. This removes them.
    """

    description = "clean up output of 'build' commands"

    def initialize_options(self):
        distutils_clean.initialize_options(self)
        self.shortcuts = None
        self.po_package = None
        self.po_directory = None

    def finalize_options(self):
        distutils_clean.finalize_options(self)
        self.shortcuts = self.distribution.shortcuts
        self.po_package = self.distribution.po_package
        self.po_directory = self.distribution.po_directory

    def run(self):
        distutils_clean.run(self)
        if not self.all:
            return

        # gettext byproducts
        if self.po_directory and self.po_package:
            pot = os.path.join(self.po_directory, self.po_package + ".pot")
            try:
                os.unlink(pot)
            except OSError:
                pass

        # Python byproducts
        def should_remove(filename):
            if (
                filename.lower()[-4:] in [".pyc", ".pyo"]
                or filename.endswith("~")
                or (filename.startswith("#") and filename.endswith("#"))
            ):
                return True
            else:
                return False

        for pathname, _dirs, files in os.walk("."):
            for filename in filter(should_remove, files):
                try:
                    os.unlink(os.path.join(pathname, filename))
                except OSError as err:
                    print(str(err))

        # setup.py byproducts
        for base in ["coverage", "build", "dist"]:
            if os.path.isdir(base):
                shutil.rmtree(base)

        # docs
        for entry in os.listdir("docs"):
            path = os.path.join("docs", entry)
            if entry.startswith("_") and os.path.isdir(path):
                shutil.rmtree(path)

        try:
            os.remove("MANIFEST")
        except OSError:
            pass


__all__ = ["Clean"]
