# -*- coding: utf-8 -*-
# Copyright 2015 Christoph Reiter
#
# This software and accompanying documentation, if any, may be freely
# used, distributed, and/or modified, in any form and for any purpose,
# as long as this notice is preserved. There is no warranty, either
# express or implied, for this software.

from __future__ import absolute_import

import os
import sys
import urllib

from distutils.core import Command


class coverage_cmd(Command):
    description = "generate test coverage data"
    user_options = [
        ("to-run=", None, "list of tests to run (default all)"),
    ]

    def initialize_options(self):
        self.to_run = []

    def finalize_options(self):
        self.options = self.distribution.coverage_options
        self.packages = self.distribution.packages
        include = set([p.split(".", 1)[0] + "*" for p in self.packages])
        self.options.setdefault("include", include)
        self.options.setdefault("directory", "coverage")

    def run(self):
        # Wipe existing modules, to make sure coverage data is properly
        # generated for them.
        for key in sys.modules.keys():
            for package in self.packages:
                if key == package or key.startswith(package + "."):
                    del sys.modules[key]
                    break

        try:
            from coverage import coverage, CoverageException
        except ImportError:
            print("Missing 'coverage' module. See "
                  "https://pypi.python.org/pypi/coverage or try "
                  "`apt-get install python-coverage`")
            return

        cov = coverage()
        cov.start()

        cmd = self.reinitialize_command("test")
        cmd.to_run = self.to_run[:]
        cmd.ensure_finalized()
        cmd.run()

        cov.stop()
        try:
            cov.html_report(**self.options)
        except CoverageException as e:
            # this fails in case js libs are missing, but the html is still
            # there, so don't fail completely
            print(e)

        dest = os.path.abspath(self.options["directory"])
        index = os.path.join(dest, "index.html")
        index_url = urllib.pathname2url(index)

        print("Coverage summary: file://%s" % index_url)
