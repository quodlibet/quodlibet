# -*- coding: utf-8 -*-
# Copyright 2007 Joe Wreschnig
#
# This software and accompanying documentation, if any, may be freely
# used, distributed, and/or modified, in any form and for any purpose,
# as long as this notice is preserved. There is no warranty, either
# express or implied, for this software.

"""translation support

This module contains commands to support building and installing
gettext message catalogs.
"""

import os
import glob
from subprocess import Popen, PIPE

from distutils.dep_util import newer
from distutils.util import change_root
from distutils.spawn import find_executable
from distutils.core import Command


class po_stats(Command):

    description = "Show translation statistics"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        self.po_directory = self.distribution.po_directory
        self.po_files = glob.glob(os.path.join(self.po_directory, "*.po"))

    def run(self):
        self.run_command("update_po")
        res = []
        for po in self.po_files:
            language = os.path.basename(po).split(".")[0]
            p = Popen(["msgfmt", "--statistics", po], stdout=PIPE, stderr=PIPE)
            output = p.communicate()[1]
            res.append((language, output))
        del p

        stats = []
        for po, r in res:
            nums = [int(p.split()[0]) for p in r.split(",")]
            while len(nums) < 3:
                nums.append(0)
            trans, fuzzy, untrans = nums
            stats.append((po, trans, fuzzy, untrans))

        stats.sort(key=lambda x: x[1], reverse=True)
        print "#" * 30
        for po, trans, fuzzy, untrans in stats:
            all_ = float(trans + fuzzy + untrans) / 100
            print ("%5s: %3d%% (+%2d%% fuzzy)" %
                   (po, trans / all_, fuzzy / all_))


class update_po(Command):

    description = "update po files"
    user_options = [
        ("lang=", None, "force update <lang>.po"),
    ]

    def initialize_options(self):
        self.po_directory = None
        self.lang = None

    def finalize_options(self):
        self.po_directory = self.distribution.po_directory
        self.po_package = self.distribution.po_package
        self.po_files = glob.glob(os.path.join(self.po_directory, "*.po"))
        self.pot_file = os.path.join(
            self.po_directory, self.po_package + ".pot")

    def _update_pot(self):
        oldpath = os.getcwd()
        os.chdir(self.po_directory)
        self.spawn(["intltool-update", "--pot",
                    "--gettext-package", self.po_package])
        os.chdir(oldpath)

        # strip POT-Creation-Date to make build reproducible
        done = False
        lines = []
        for line in open(self.pot_file, "rb"):
            if not done and line.startswith('"POT-Creation-Date:'):
                done = True
                continue
            lines.append(line)
        with open(self.pot_file, "wb") as h:
            h.write("".join(lines))

    def _update_po(self, po):
        assert po in self.po_files
        oldpath = os.getcwd()
        os.chdir(self.po_directory)
        code = os.path.basename(po[:-3])
        self.spawn(["intltool-update", "--dist",
                    "--gettext-package", self.po_package,
                    code])
        os.chdir(oldpath)

    def run(self):
        if find_executable("intltool-update") is None:
            raise SystemExit("Error: 'intltool' not found.")

        # if lang is given, force update pot and the specific po
        if self.lang is not None:
            po = os.path.join(self.po_directory, self.lang + ".po")
            if po not in self.po_files:
                raise SystemExit("Error: %r not found" % po)
            self._update_pot()
            self._update_po(po)
            return

        infilename = os.path.join(self.po_directory, "POTFILES.in")
        with open(infilename, "rb") as h:
            infiles = h.read().splitlines()

        # if any of the in files is newer than the pot, update the pot
        for filename in infiles:
            if newer(filename, self.pot_file):
                self._update_pot()
                break
        else:
            print "not pot update"

        # if the pot file is newer than any of the po files, update that po
        for po in self.po_files:
            if newer(self.pot_file, po):
                self._update_po(po)


class build_mo(Command):
    """build message catalog files

    Build message catalog (.mo) files from .po files using xgettext
    and intltool.  These are placed directly in the build tree.
    """

    description = "build message catalog files"
    user_options = []

    def initialize_options(self):
        self.skip_po_update = None
        self.build_base = None
        self.po_package = None
        self.po_files = None
        self.pot_file = None

    def finalize_options(self):
        self.po_directory = self.distribution.po_directory
        self.po_package = self.distribution.po_package
        self.set_undefined_options('build', ('build_base', 'build_base'))
        self.set_undefined_options(
            'build', ('skip_po_update', 'skip_po_update'))
        self.po_files = glob.glob(os.path.join(self.po_directory, "*.po"))
        self.pot_file = os.path.join(
            self.po_directory, self.po_package + ".pot")

    def run(self):
        if find_executable("msgfmt") is None:
            raise SystemExit("Error: 'gettext' not found.")

        # It's OK to skip po update for building release tarballs, since
        # things are updated right before release...
        if not self.skip_po_update:
            self.run_command("update_po")

        basepath = os.path.join(self.build_base, 'share', 'locale')

        for po in self.po_files:
            language = os.path.basename(po).split(".")[0]
            fullpath = os.path.join(basepath, language, "LC_MESSAGES")
            destpath = os.path.join(fullpath, self.po_package + ".mo")
            if newer(po, destpath):
                self.mkpath(fullpath)
                self.spawn(["msgfmt", "-o", destpath, po])


class install_mo(Command):
    """install message catalog files

    Copy compiled message catalog files into their installation
    directory, $prefix/share/locale/$lang/LC_MESSAGES/$package.mo.
    """

    description = "install message catalog files"
    user_options = []

    def initialize_options(self):
        self.skip_build = None
        self.build_base = None
        self.install_base = None
        self.root = None
        self.outfiles = []

    def finalize_options(self):
        self.set_undefined_options('build', ('build_base', 'build_base'))
        self.set_undefined_options(
            'install',
            ('root', 'root'),
            ('install_base', 'install_base'),
            ('skip_build', 'skip_build'))

    def get_outputs(self):
        return self.outfiles

    def run(self):
        if not self.skip_build:
            self.run_command('build_mo')
        src = os.path.join(self.build_base, "share", "locale")
        dest = os.path.join(self.install_base, "share", "locale")
        if self.root is not None:
            dest = change_root(self.root, dest)
        out = self.copy_tree(src, dest)
        self.outfiles.extend(out)

__all__ = ["build_mo", "install_mo", "po_stats"]
