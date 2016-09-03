# -*- coding: utf-8 -*-
# Copyright 2014, 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import re
import pprint

from gi.repository import Gtk

from tests import TestCase


def iter_py_paths():
    """Iterates over all Python source files that are part of Quod Libet"""

    import quodlibet
    root = os.path.dirname(quodlibet.__path__[0])

    skip = [os.path.join(root, "docs")]
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
                    match = match or re.search("coding[:=]\s*([-\w.]+)", line)
                    if i >= 2:
                        break
                if match:
                    match = match.group(1)
                self.assertEqual(match, "utf-8",
                                 msg="%s has no utf-8 source encoding set\n"
                                     "Insert:\n# -*- coding: utf-8 -*-" % path)


class TLicense(TestCase):

    ALLOWED = ["""This program is free software; you can redistribute it \
and/or modify it under the terms of the GNU General Public License version 2 \
as published by the Free Software Foundation""",
               """This program is free software; you can redistribute it \
and/or modify it under the terms of version 2 of the GNU General Public \
License as published by the Free Software Foundation""",
               """This software and accompanying documentation, if any, may \
be freely used, distributed, and/or modified, in any form and for any \
purpose, as long as this notice is preserved. There is no warranty, either \
express or implied, for this software""",
               """This program is free software; you can redistribute it \
and/or modify it under the terms of the GNU General Public License as \
published by the Free Software Foundation; either version 2, or (at your \
option) any later version. This program is distributed in the hope that it \
will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty o\
f MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General \
Public License for more details. You should have received a copy of the \
GNU General Public License along with this program; if not, write to the \
Free Software Foundation, Inc., 59 Temple Place - Suite 330, Boston, \
MA 02111-1307, USA""",
"""Permission is hereby granted, free of charge, to any person obtaining \
a copy of this software and associated documentation files (the "Software"), \
to deal in the Software without restriction, including without limitation \
the rights to use, copy, modify, merge, publish, distribute, sublicense, \
and/or sell copies of the Software, and to permit persons to whom the \
Software is furnished to do so, subject to the following conditions: The \
above copyright notice and this permission notice shall be included in all \
copies or substantial portions of the Software""",
]

    def test_main(self):
        missing = []
        for path in iter_py_paths():
            header = ""
            with open(path, "rb") as h:
                for line in h:
                    line = line.strip()
                    if not line.startswith("#"):
                        break
                    header += line.lstrip("# ") + "\n"

            norm = " ".join(header.strip().split())
            maybe_license = norm.rstrip(".")
            for license_ in self.ALLOWED:
                if maybe_license.endswith(license_):
                    maybe_license = license_
                    break

            if maybe_license not in self.ALLOWED:
                missing.append(path)

        self.assertFalse(missing, msg="Missing license: %r" % missing)


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
                data = h.read()
                for r in res:
                    match = r.search(data)
                    if match:
                        group = match.group(1)
                        if group not in white:
                            errors.setdefault(group, []).append(path)

        self.assertFalse(errors, msg=pprint.pformat(errors))
