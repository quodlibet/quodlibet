# -*- coding: utf-8 -*-
# Copyright 2014, 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import re
import pprint

from gi.repository import Gtk

from quodlibet.util import get_module_dir

from tests import TestCase


def iter_py_paths():
    """Iterates over all Python source files that are part of Quod Libet"""

    import quodlibet
    root = os.path.dirname(get_module_dir(quodlibet))

    skip = [
        os.path.join(root, "docs"),
        os.path.join(root, "quodlibet", "packages"),
    ]
    for dirpath, dirnames, filenames in os.walk(root):
        if any((dirpath.startswith(s + os.sep) or s == dirpath)
               for s in skip):
            continue

        for filename in filenames:
            if filename.endswith('.py'):
                yield os.path.join(dirpath, filename)


class TSourceEncoding(TestCase):
    """Enforce utf-8 source encoding everywhere.
    Plus give helpful message for fixing it.
    """

    def test_main(self):
        for path in iter_py_paths():
            with open(path, "rb") as h:
                match = None
                for i, line in enumerate(h):
                    # https://www.python.org/dev/peps/pep-0263/
                    match = match or re.search(b"coding[:=]\s*([-\w.]+)", line)
                    if i >= 2:
                        break
                if match:
                    match = match.group(1)
                self.assertEqual(match, b"utf-8",
                                 msg="%s has no utf-8 source encoding set\n"
                                     "Insert:\n# -*- coding: utf-8 -*-" % path)


class TLicense(TestCase):

    ALLOWED = ["""
This program is free software; you can redistribute it
and/or modify it under the terms of the GNU General Public License version 2
as published by the Free Software Foundation
""", """
This program is free software; you can redistribute it
and/or modify it under the terms of version 2 of the GNU General Public
License as published by the Free Software Foundation
""", """
This software and accompanying documentation, if any, may
be freely used, distributed, and/or modified, in any form and for any
purpose, as long as this notice is preserved. There is no warranty, either
express or implied, for this software
""", """
This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
""", """
Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
""",
]

    def test_main(self):
        allowed = []
        for license in self.ALLOWED:
            allowed.append("".join(license.split()))

        found = set()
        missing = []
        for path in iter_py_paths():
            header = b""
            with open(path, "rb") as h:
                for line in h:
                    line = line.strip()
                    if not line.startswith(b"#"):
                        break
                    header += line.lstrip(b"# ") + b"\n"

            norm = b"".join(header.split())
            norm = norm.decode("utf-8")

            for license_ in allowed:
                if license_ in norm:
                    found.add(license_)
                    break
            else:
                missing.append(path)

        self.assertFalse(missing, msg="Missing license: %r" % missing)
        assert len(allowed) == len(found)


class TStockIcons(TestCase):

    def test_main(self):

        # gtk setting keys start like stock icons, so white list them
        white = [x.replace("_", "-") for x in
                 dir(Gtk.Settings.get_default().props) if x.startswith("gtk_")]
        # older gtk doesn't have those, but we still have them in the source
        white.append("gtk-dialogs-use-header")
        white.append("gtk-primary-button-warps-slider")
        # some more..
        white.append("gtk-tooltip")
        white.append("gtk-")
        white.append("gtk-update-icon-cache-")

        res = map(re.compile, [
            "(Gtk\\.STOCK_[_A-Z]*)",
            "[\"\'](gtk-[\\-a-z]*)",
        ])
        errors = {}
        for path in iter_py_paths():
            with open(path, "rb") as h:
                if path.endswith(("icons.py", "test_source.py")):
                    continue
                data = h.read().decode("utf-8")
                for r in res:
                    match = r.search(data)
                    if match:
                        group = match.group(1)
                        if group not in white:
                            errors.setdefault(group, []).append(path)

        self.assertFalse(errors, msg=pprint.pformat(errors))
