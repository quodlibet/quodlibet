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


class BuildSphinx(Command):
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
        docs_root = "docs"
        guide_root = os.path.join(docs_root, "guide")
        target = os.path.join(self.build_dir, "sphinx")

        src_dir = guide_root if not self.all else docs_root
        self.spawn(
            [
                sys.executable,
                "-m",
                "sphinx",
                "-j",
                "auto",
                "-b",
                "html",
                "-c",
                docs_root,
                "-n",
                "-E",
                "-W",
                src_dir,
                target,
            ]
        )
