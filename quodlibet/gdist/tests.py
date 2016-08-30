# -*- coding: utf-8 -*-
# Copyright 2014 Christoph Reiter
#
# This software and accompanying documentation, if any, may be freely
# used, distributed, and/or modified, in any form and for any purpose,
# as long as this notice is preserved. There is no warranty, either
# express or implied, for this software.

from __future__ import absolute_import

import os
import sys
import subprocess
import tarfile

from distutils.core import Command
from distutils import dir_util
from distutils.command.sdist import sdist


class test_cmd(Command):
    description = "run automated tests"
    user_options = [
        ("to-run=", None, "list of tests to run (default all)"),
        ("suite=", None, "test suite (folder) to run (default 'tests')"),
        ("strict", None, "make glib warnings / errors fatal"),
        ("all", None, "run all suites"),
        ("exitfirst", "x", "stop after first failing test"),
        ("no-network", "n", "skip tests requiring a network connection"),
    ]

    def initialize_options(self):
        self.to_run = []
        self.suite = None
        self.strict = False
        self.all = False
        self.exitfirst = False
        self.no_network = False

    def finalize_options(self):
        if self.to_run:
            self.to_run = self.to_run.split(",")
        self.strict = bool(self.strict)
        self.all = bool(self.all)
        self.suite = self.suite and str(self.suite)
        self.exitfirst = bool(self.exitfirst)
        self.no_network = bool(self.no_network)

    def run(self):
        import tests

        suite = self.suite
        if self.all:
            suite = None

        status = tests.unit(run=self.to_run, suite=suite,
                            strict=self.strict, exitfirst=self.exitfirst,
                            network=(not self.no_network or self.all),
                            quality=self.all)
        if status != 0:
            raise SystemExit(status)


class quality_cmd(Command):
    description = "Run pep8/pyflakes tests"
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
        self.spawn([sys.executable, "setup.py", "quality"])
        self.spawn([sys.executable, "setup.py", "build"])
        self.spawn([sys.executable, "setup.py", "build_sphinx"])
        self.spawn([sys.executable, "setup.py", "install",
                    "--prefix", "../prefix", "--record", "../log.txt"])
        os.chdir(old_pwd)

    def run(self):
        sdist.run(self)
        self._check_manifest()
        self._check_dist()
