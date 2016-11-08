# -*- coding: utf-8 -*-
# Copyright 2016 Christoph Reiter
#
# This software and accompanying documentation, if any, may be freely
# used, distributed, and/or modified, in any form and for any purpose,
# as long as this notice is preserved. There is no warranty, either
# express or implied, for this software.

"""
A distutils command which handles a subset of setuptools entry points.
Use this instead of "scripts". Requires setuptools on Windows.
"""

import os
import sys
import struct
import stat
import imp

from .util import Command


def parse_entry(line):
    """Splits up things like 'exfalso=quodlibet.exfalso:main'"""

    name, import_path = line.split("=", 1)
    module, func = import_path.split(":", 1)
    return (name.strip(), module.strip(), func.strip())


def get_launcher_content(type_):
    """Returns the content of an exe launcher. This requires setuptools.
    """

    assert type_ in ("cli", "gui")

    # we can't import setuptools because it monkey patches distutils
    # and will break any commands following this one
    file_, pathname, description = imp.find_module("setuptools")
    if file_ is not None:
        file_.close()

    is_64bit = struct.calcsize("P") == 8
    exe = "%s-%s.exe" % (type_, "64" if is_64bit else "32")
    with open(os.path.join(pathname, exe), "rb") as h:
        return h.read()


def get_script_content(module, func, type_):
    """
    Args:
        modules (str): e.g. quodlibet.main
        func (str): e.g. main
        type_ (str): either gui or cli
    Returns:
        str: content of the start script
    """

    assert type_ in ("gui", "cli")

    lines = []
    if os.name == "nt":
        if type_ == "gui":
            lines.append("#!python%dw.exe" % sys.version_info[0])
        else:
            lines.append("#!python%d.exe" % sys.version_info[0])
    else:
        lines.append("#!/usr/bin/env python%d" % sys.version_info[0])
    lines.extend([
        "import sys",
        "from %s import %s" % (module, func),
        "if __name__ == '__main__':",
        "    sys.exit(%s())" % func
    ])
    return os.linesep.join(lines)


class build_launchers(Command):
    description = "build launchers"
    user_options = []

    def initialize_options(self):
        self.build_dir = None
        self.launchers = None

    def finalize_options(self):
        self.set_undefined_options('build',
                                   ('build_scripts', 'build_dir'))
        self.launchers = self.distribution.launchers

    def run(self):
        self.mkpath(self.build_dir)

        for type_, entries in self.launchers.items():
            type_ = {"console_scripts": "cli", "gui_scripts": "gui"}[type_]
            for entry in entries:
                name, module, func = parse_entry(entry)
                new_path = os.path.join(self.build_dir, name)

                with open(new_path, "wb") as h:
                    h.write(get_script_content(module, func, type_))
                if os.name == "nt":
                    with open(new_path + "-script.py", "wb") as h:
                        h.write(get_script_content(module, func, type_))

                    with open(new_path + ".exe", "wb") as h:
                        h.write(get_launcher_content(type_))


class install_launchers(Command):
    description = "install launcher files"
    user_options = []

    def initialize_options(self):
        self.install_dir = None
        self.build_dir = None
        self.outfiles = []

    def finalize_options(self):
        self.set_undefined_options('install',
                                   ('install_scripts', 'install_dir'))
        self.set_undefined_options('build', ('build_scripts', 'build_dir'))

    def get_outputs(self):
        return self.outfiles

    def run(self):
        self.outfiles = self.copy_tree(self.build_dir, self.install_dir)

        if os.name == 'posix':
            for file_ in self.get_outputs():
                mode = ((os.stat(file_)[stat.ST_MODE]) | 0o555) & 0o7777
                os.chmod(file_, mode)
