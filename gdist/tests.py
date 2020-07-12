# Copyright 2014-2016 Christoph Reiter
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

from __future__ import absolute_import

import os
import sys
import subprocess
import tarfile
import fnmatch
from distutils import dir_util

from .util import Command, get_dist_class


class test_cmd(Command):
    description = "run automated tests"
    user_options = [
        ("to-run=", None, "list of tests to run (default all)"),
        ("suite=", None, "test suite (folder) to run (default 'tests')"),
        ("strict", None, "make glib warnings / errors fatal"),
        ("all", None, "run all suites"),
        ("exitfirst", "x", "stop after first failing test"),
        ("no-network", "n", "skip tests requiring a network connection"),
        ("no-quality", "n", "skip tests for code quality"),
    ]

    def initialize_options(self):
        self.to_run = []
        self.suite = None
        self.strict = False
        self.all = False
        self.exitfirst = False
        self.no_network = False
        self.no_quality = False

    def finalize_options(self):
        if self.to_run:
            self.to_run = self.to_run.split(",")
        self.strict = bool(self.strict)
        self.all = bool(self.all)
        self.suite = self.suite and str(self.suite)
        self.exitfirst = bool(self.exitfirst)
        self.no_network = bool(self.no_network)
        self.no_quality = bool(self.no_quality)

    def run(self):
        import tests

        suite = self.suite
        if self.all:
            suite = None

        status = tests.unit(run=self.to_run, suite=suite,
                            strict=self.strict, exitfirst=self.exitfirst,
                            network=(not self.no_network or self.all),
                            quality=(not self.no_quality or self.all))
        if status != 0:
            raise SystemExit(status)


class quality_cmd(Command):
    description = "Run flake8/mypy tests"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import tests

        status = tests.unit(suite="quality", quality=True)
        if status != 0:
            raise SystemExit(status)


sdist = get_dist_class("sdist")


class distcheck_cmd(sdist):
    description = "run tests on a fresh sdist"

    def _check_manifest(self):
        assert self.get_archive_files()

        # make sure MANIFEST.in includes all tracked files
        if subprocess.call(["git", "status"],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE) == 0:
            # contains the packaged files after run() is finished
            included_files = self.filelist.files
            assert included_files

            process = subprocess.Popen(
                ["git", "ls-tree", "-r", "HEAD", "--name-only"],
                stdout=subprocess.PIPE, universal_newlines=True)
            out, err = process.communicate()
            assert process.returncode == 0

            tracked_files = out.splitlines()
            ignore_tracked = [
                "dev-utils/*",
                ".github/*",
                ".ci/*",
                ".codecov.yml",
                ".git*",
            ]
            tracked_files = [
                p for p in tracked_files if not
                any(fnmatch.fnmatch(p, i) for i in ignore_tracked)]

            diff = set(tracked_files) - set(included_files)
            assert not diff, (
                "Not all tracked files included in tarball, check MANIFEST.in",
                diff)

    def _check_dist(self):
        assert self.get_archive_files()

        distcheck_dir = os.path.join(self.dist_dir, "distcheck")
        if os.path.exists(distcheck_dir):
            dir_util.remove_tree(distcheck_dir)
        self.mkpath(distcheck_dir)

        archive = self.get_archive_files()[0]
        tfile = tarfile.open(archive, "r:gz")
        tfile.extractall(distcheck_dir)
        tfile.close()

        name = self.distribution.get_fullname()
        extract_dir = os.path.join(distcheck_dir, name)

        old_pwd = os.getcwd()
        os.chdir(extract_dir)
        self.spawn([sys.executable, "setup.py", "test"])
        self.spawn([sys.executable, "setup.py", "build"])
        self.spawn([sys.executable, "setup.py", "build_sphinx"])
        self.spawn([sys.executable, "setup.py", "install",
                    "--root", "../prefix", "--record", "../log.txt"])
        os.chdir(old_pwd)

    def run(self):
        sdist.run(self)
        self._check_manifest()
        self._check_dist()
