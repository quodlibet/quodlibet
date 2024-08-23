#!/usr/bin/env python3
# Copyright 2010-2015 Christoph Reiter
#           2015 Nick Boultbee
#           2010 Steven Robertson
#           2007-2008 Joe Wreschnig
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
import types

from gdist import GDistribution, setup


def exec_module(path):
    """Executes the Python file at `path` and returns it as the module"""

    globals_ = {}
    with open(path, encoding="utf-8") as h:
        exec(h.read(), globals_)
    module = types.ModuleType("")
    module.__dict__.update(globals_)
    return module


def main():
    assert sys.version_info[0] == 3, "Quod Libet is Python 3 only now"

    # distutils depends on setup.py beeing executed from the same dir.
    # Most of our custom commands work either way, but this makes
    # it work in all cases.
    os.chdir(os.path.dirname(os.path.realpath(__file__)))

    const = exec_module(os.path.join("quodlibet", "const.py"))

    # convert to a setuptools compatible version string
    version = const.VERSION_TUPLE
    if version[-1] == -1:
        version_string = ".".join(map(str, version[:-1])) + ".dev0"
    else:
        version_string = ".".join(map(str, version))

    package_path = "quodlibet"
    packages = []
    for root, _dirnames, filenames in os.walk(package_path):
        if "__init__.py" in filenames:
            relpath = os.path.relpath(root, os.path.dirname(package_path))
            package_name = relpath.replace(os.sep, ".")
            packages.append(package_name)
    assert packages

    setup_kwargs = {
        "distclass": GDistribution,
        "name": "quodlibet",
        "version": version_string,
        "url": "https://quodlibet.readthedocs.org",
        "description": "a music library, tagger, and player",
        "author": "Joe Wreschnig, Michael Urman, & others",
        "author_email": "quod-libet-development@googlegroups.com",
        "maintainer": "Steven Robertson and Christoph Reiter",
        "license": "GPL-2.0-or-later",
        "packages": packages,
        "package_data": {
            "quodlibet": [
                "images/hicolor/*/*/*.png",
                "images/hicolor/*/*/*.svg",
            ],
        },
        "scripts": [
            "quodlibet.py",
            "exfalso.py",
            "operon.py",
        ],
        "po_directory": "po",
        "po_package": "quodlibet",
        "shortcuts": [
            "data/io.github.quodlibet.QuodLibet.desktop",
            "data/io.github.quodlibet.ExFalso.desktop"
        ],
        "dbus_services": [
            "data/net.sacredchao.QuodLibet.service",
            # https://github.com/quodlibet/quodlibet/issues/1268
            # "data/org.mpris.MediaPlayer2.quodlibet.service",
            # "data/org.mpris.quodlibet.service",
        ],
        "appdata": [
            "data/io.github.quodlibet.QuodLibet.appdata.xml",
            "data/io.github.quodlibet.ExFalso.appdata.xml",
        ],
        "man_pages": [
            "data/quodlibet.1",
            "data/exfalso.1",
            "data/operon.1",
        ],
        "search_provider":
            "data/io.github.quodlibet.QuodLibet-search-provider.ini",
        "bash_completions": [
            ("data/quodlibet.bash", "quodlibet"),
            ("data/quodlibet.bash", "operon"),
        ],
        "zsh_completions": [
            ("data/quodlibet.zsh", "_quodlibet"),
        ],
        "coverage_options": {
            "directory": "coverage",
        },
    }

    setup(**setup_kwargs)


if __name__ == "__main__":
    main()
