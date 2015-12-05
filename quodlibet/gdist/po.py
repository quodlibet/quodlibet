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
from tempfile import mkstemp

from distutils.dep_util import newer
from distutils.spawn import find_executable
from distutils.core import Command
from distutils.errors import DistutilsOptionError

from . import gettextutil


class po_stats(Command):

    description = "Show translation statistics"
    user_options = []

    def initialize_options(self):
        self.po_directory = None
        self.po_files = None

    def finalize_options(self):
        self.po_directory = self.distribution.po_directory
        self.po_package = self.distribution.po_package
        self.po_files = glob.glob(os.path.join(self.po_directory, "*.po"))

    def run(self):
        gettextutil.update_pot(self.po_directory, self.po_package)

        res = []
        for po in self.po_files:
            language = os.path.basename(po).split(".")[0]

            fd, temp_path = mkstemp(".po")
            try:
                os.close(fd)
                gettextutil.update_po(self.po_directory, self.po_package,
                                      language, output_file=temp_path)
                proc = Popen(["msgfmt", "-o", "/dev/null", "--statistics",
                              temp_path], stdout=PIPE, stderr=PIPE)
                output = proc.communicate()[1]
                res.append((language, output))
            finally:
                os.remove(temp_path)

        stats = []
        for po, r in res:
            nums = [int(p.split()[0]) for p in r.split(",")]
            while len(nums) < 3:
                nums.append(0)
            trans, fuzzy, untrans = nums
            stats.append((po, trans, fuzzy, untrans))

        stats.sort(key=lambda x: x[1], reverse=True)
        print("#" * 30)
        for po, trans, fuzzy, untrans in stats:
            all_ = float(trans + fuzzy + untrans) / 100
            print("%5s: %3d%% (+%2d%% fuzzy)" %
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
        gettextutil.update_pot(self.po_directory, self.po_package)

    def _update_po(self, po):
        assert po in self.po_files
        lang_code = os.path.basename(po[:-3])
        gettextutil.update_po(self.po_directory, self.po_package, lang_code)

    def run(self):
        try:
            gettextutil.check_version()
        except gettextutil.GettextError as e:
            raise SystemExit(e)

        # if lang is given, force update pot and the specific po
        if self.lang is not None:
            po = os.path.join(self.po_directory, self.lang + ".po")
            if po not in self.po_files:
                raise SystemExit("Error: %r not found" % po)
            self._update_pot()
            self._update_po(po)
            return

        self._update_pot()

        # if the pot file is newer than any of the po files, update that po
        for po in self.po_files:
            if newer(self.pot_file, po):
                self._update_po(po)


class create_po(Command):

    description = "create a new po file"
    user_options = [
        ("lang=", None, "create <lang>.po"),
    ]

    def initialize_options(self):
        self.po_directory = None
        self.lang = None

    def finalize_options(self):
        self.po_directory = self.distribution.po_directory
        self.po_package = self.distribution.po_package
        self.pot_file = os.path.join(
            self.po_directory, self.po_package + ".pot")
        if not self.lang:
            raise DistutilsOptionError("no --lang= given")

    def run(self):
        try:
            gettextutil.check_version()
        except gettextutil.GettextError as e:
            raise SystemExit(e)

        gettextutil.update_pot(self.po_directory, self.po_package)
        path = gettextutil.create_po(
            self.po_directory, self.po_package, self.lang)
        gettextutil.update_po(self.po_directory, self.po_package, self.lang)
        print("Created %r" % os.path.abspath(path))


def strip_pot_date(path):
    """strip POT-Creation-Date from po/pot"""

    done = False
    lines = []
    for line in open(path, "rb"):
        if not done and line.startswith('"POT-Creation-Date:'):
            done = True
            continue
        lines.append(line)

    with open(path, "wb") as h:
        h.write("".join(lines))


class build_mo(Command):
    """build message catalog files

    Build message catalog (.mo) files from .po files using xgettext
    and intltool.  These are placed directly in the build tree.
    """

    description = "build message catalog files"
    user_options = []

    def initialize_options(self):
        self.build_base = None
        self.po_package = None
        self.po_files = None

    def finalize_options(self):
        self.po_directory = self.distribution.po_directory
        self.po_package = self.distribution.po_package
        self.set_undefined_options('build', ('build_base', 'build_base'))
        self.po_files = glob.glob(os.path.join(self.po_directory, "*.po"))

    def run(self):
        if find_executable("msgfmt") is None:
            raise SystemExit("Error: 'gettext' not found.")

        gettextutil.update_pot(self.po_directory, self.po_package)

        basepath = os.path.join(self.build_base, 'share', 'locale')
        for po in self.po_files:
            language = os.path.basename(po).split(".")[0]
            fullpath = os.path.join(basepath, language, "LC_MESSAGES")
            destpath = os.path.join(fullpath, self.po_package + ".mo")
            if newer(po, destpath):
                self.mkpath(fullpath)

                # strip POT-Creation-Date from po/mo to make build reproducible
                fd, temp_path = mkstemp(".po")
                try:
                    os.close(fd)
                    gettextutil.update_po(self.po_directory, self.po_package,
                                          language, output_file=temp_path)
                    strip_pot_date(temp_path)
                    self.spawn(["msgfmt", "-o", destpath, temp_path])
                finally:
                    os.remove(temp_path)


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
        self.install_dir = None
        self.outfiles = []

    def finalize_options(self):
        self.set_undefined_options('build', ('build_base', 'build_base'))
        self.set_undefined_options(
            'install',
            ('install_data', 'install_dir'),
            ('skip_build', 'skip_build'))

    def get_outputs(self):
        return self.outfiles

    def run(self):
        if not self.skip_build:
            self.run_command('build_mo')
        src = os.path.join(self.build_base, "share", "locale")
        dest = os.path.join(self.install_dir, "share", "locale")
        out = self.copy_tree(src, dest)
        self.outfiles.extend(out)

__all__ = ["build_mo", "install_mo", "po_stats"]
