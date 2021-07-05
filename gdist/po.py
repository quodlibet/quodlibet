# Copyright 2007 Joe Wreschnig
#           2009-2010,2012-2016 Christoph Reiter
#           2021 Nick Boultbee
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

"""translation support

This module contains commands to support building and installing
gettext message catalogs.
"""

import os
import shutil
from pathlib import Path
from tempfile import mkstemp
from distutils.errors import DistutilsOptionError
from distutils.dep_util import newer_group, newer
from typing import Optional

from .util import Command
from . import gettextutil


class po_stats(Command):

    description = "Show translation statistics"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        po_directory = Path(self.distribution.po_directory)

        with gettextutil.create_pot(po_directory) as pot_path:
            res = []
            for language in gettextutil.list_languages(po_directory):
                fd, temp_path = mkstemp(".po")
                temp_path = Path(temp_path)
                try:
                    os.close(fd)
                    po_path = gettextutil.get_po_path(po_directory, language)
                    gettextutil.update_po(pot_path, po_path, temp_path)
                    output = gettextutil.po_stats(temp_path)
                    res.append((language, output))
                finally:
                    temp_path.unlink()

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
        self.lang = None

    def finalize_options(self):
        pass

    def run(self):
        try:
            gettextutil.check_version()
        except gettextutil.GettextError as e:
            raise SystemExit(e)

        po_directory = Path(self.distribution.po_directory)

        langs = gettextutil.list_languages(po_directory)
        if self.lang is not None:
            if self.lang not in langs:
                raise SystemExit(f"Error: {self.lang} not found")
            else:
                langs = [self.lang]

        with gettextutil.create_pot(po_directory) as pot_path:
            for lang in langs:
                po_path = gettextutil.get_po_path(po_directory, lang)
                gettextutil.update_po(pot_path, po_path)


class create_po(Command):

    description = "create a new po file"
    user_options = [
        ("lang=", None, "create <lang>.po"),
    ]

    def initialize_options(self):
        self.lang = None

    def finalize_options(self):
        if not self.lang:
            raise DistutilsOptionError("no --lang= given")

    def run(self):
        try:
            gettextutil.check_version()
        except gettextutil.GettextError as e:
            raise SystemExit(e)

        po_directory = Path(self.distribution.po_directory)
        po_path = gettextutil.get_po_path(po_directory, self.lang)
        with gettextutil.create_pot(po_directory) as pot_path:
            gettextutil.create_po(pot_path, po_path)
            print(f"Created {po_path.absolute()}")


class create_pot(Command):

    description = "create a new pot file"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            gettextutil.check_version()
        except gettextutil.GettextError as e:
            raise SystemExit(e)

        po_package = self.distribution.po_package
        po_directory = Path(self.distribution.po_directory)
        with gettextutil.create_pot(po_directory) as pot_path:
            dest = po_directory / f"{po_package}.pot"
            shutil.copy(pot_path, dest)
            strip_pot_date(dest)
            print(f"Created {dest.absolute()}")


def strip_pot_date(path):
    """strip POT-Creation-Date from po/pot"""

    done = False
    lines = []
    for line in open(path, "rb"):
        if not done and line.startswith(b'"POT-Creation-Date:'):
            done = True
            continue
        lines.append(line)

    with open(path, "wb") as h:
        h.write(b"".join(lines))


class build_po(Command):

    description = "update and copy .po files to the build dir"
    user_options = []

    def initialize_options(self):
        self.build_base = None
        self.po_build_dir: Optional[Path] = None

    def finalize_options(self):
        self.set_undefined_options('build', ('build_base', 'build_base'))
        self.po_build_dir = Path(self.build_base) / '_po_build'

    def run(self):
        po_directory = Path(self.distribution.po_directory)
        langs = gettextutil.list_languages(po_directory)

        pot_deps = gettextutil.get_pot_dependencies(po_directory)
        to_build = []
        for language in langs:
            po_path = gettextutil.get_po_path(po_directory, language)
            out_path = gettextutil.get_po_path(self.po_build_dir, language)
            if newer_group([str(p) for p in pot_deps + [po_path]], str(out_path)):
                to_build.append((po_path, out_path))

        if not to_build:
            return

        self.mkpath(str(self.po_build_dir))
        with gettextutil.create_pot(po_directory) as pot_path:
            for po_path, out_path in to_build:
                gettextutil.update_po(pot_path, po_path, out_path)
                # strip POT-Creation-Date from po/mo to make build
                # reproducible
                strip_pot_date(out_path)
        gettextutil.update_linguas(self.po_build_dir)


class build_mo(Command):
    """build message catalog files

    Build message catalog (.mo) files from .po files using gettext.
    These are placed directly in the build tree.
    """

    description = "build message catalog files"
    user_options = [
        ("lang=", None, "build mo for <lang>"),
    ]

    def initialize_options(self):
        self.build_base: Optional[Path] = None
        self.lang = None
        self.po_build_dir: Optional[Path] = None

    def finalize_options(self):
        self.set_undefined_options('build', ('build_base', 'build_base'))
        self.set_undefined_options(
            'build_po', ('po_build_dir', 'po_build_dir'))

    def run(self):
        self.run_command("build_po")

        po_package = self.distribution.po_package

        langs = gettextutil.list_languages(self.po_build_dir)
        if self.lang is not None:
            if self.lang not in langs:
                raise SystemExit("Error: %r not found" % self.lang)
            else:
                langs = [self.lang]

        basepath = self.build_base / "share" / "locale"
        for language in langs:
            fullpath = basepath / language / "LC_MESSAGES"
            destpath = fullpath / f"{po_package}.mo"

            self.mkpath(str(fullpath))

            po_path = gettextutil.get_po_path(self.po_build_dir, language)
            if newer(str(po_path), str(destpath)):
                gettextutil.compile_po(po_path, destpath)


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

__all__ = ["build_mo", "install_mo", "po_stats", "update_po"]
