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

    print os.path.realpath(__file__)
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


class TStockIcons(TestCase):

    def test_main(self):

        # gtk setting keys start like stock icons, so white list them
        white = [x.replace("_", "-") for x in
                 dir(Gtk.Settings.get_default().props) if x.startswith("gtk_")]
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
