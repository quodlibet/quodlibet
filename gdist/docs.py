# Copyright 2015-2016 Christoph Reiter
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

import os
import sys

from .util import Command


class build_sphinx(Command):
    description = "build sphinx documentation"
    user_options = [
        ("build-dir=", "d", "build directory"),
        ("all", "a", "build all docs, not just the user guide"),
    ]

    def initialize_options(self):
        self.build_dir = None
        self.all = False

    def finalize_options(self):
        self.build_dir = self.build_dir or "build"
        self.all = bool(self.all)

    def run(self):
        DOCS_ROOT = "docs"
        GUIDE_ROOT = os.path.join(DOCS_ROOT, "guide")
        TARGET = os.path.join(self.build_dir, "sphinx")

        srcdir = GUIDE_ROOT if not self.all else DOCS_ROOT
        self.spawn([sys.executable, "-m", "sphinx",
                    "-j", "auto", "-b", "html", "-c", DOCS_ROOT,
                    "-n", "-E", "-W", srcdir, TARGET])
