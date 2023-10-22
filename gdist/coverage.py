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
from urllib.request import pathname2url

from .util import Command


class CoverageCmd(Command):
    description = "generate test coverage data"
    user_options = [
        ("to-run=", None, "list of tests to run (default all)"),
    ]

    def initialize_options(self):
        self.to_run = []

    def finalize_options(self):
        self.options = self.distribution.coverage_options
        self.packages = self.distribution.packages
        include = {p.split(".", 1)[0] + "*" for p in self.packages}
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
        index_url = pathname2url(index)

        print("Coverage summary: file://%s" % index_url)
