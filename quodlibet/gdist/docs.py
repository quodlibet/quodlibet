# -*- coding: utf-8 -*-
# Copyright 2015 Christoph Reiter
#
# This software and accompanying documentation, if any, may be freely
# used, distributed, and/or modified, in any form and for any purpose,
# as long as this notice is preserved. There is no warranty, either
# express or implied, for this software.

import os

from distutils.core import Command


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
        self.spawn(["sphinx-build", "-b", "html", "-c", DOCS_ROOT,
                    "-n", "-E", srcdir, TARGET])
