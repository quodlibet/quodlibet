# -*- coding: utf-8 -*-
# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import subprocess

from quodlibet.util.path import iscommand
from quodlibet import util

from tests import TestCase, mkstemp, skipUnless


QLDATA_DIR = os.path.join(os.path.dirname(util.get_module_dir()), "data")


class _TAppDataFileMixin(object):
    PATH = None

    def test_filename(self):
        self.assertTrue(self.PATH.endswith(".appdata.xml.in"))

    def test_validate(self):
        # strip translatable prefix from tags
        from xml.etree import ElementTree
        tree = ElementTree.parse(self.PATH)
        for x in tree.iter():
            if x.tag.startswith("_"):
                x.tag = x.tag[1:]
        fd, name = mkstemp(suffix=".appdata.xml")
        os.close(fd)

        with open(name, "wb") as temp:
            header = open(self.PATH, "rb").read().splitlines()[0]
            temp.write(header + b"\n")
            temp.write(ElementTree.tostring(tree.getroot(), encoding="utf-8"))

        # pass to desktop-file-validate
        try:
            subprocess.check_output(
                ["appstream-util", "validate", "--nonet", name],
                stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            raise Exception(e.output)
        finally:
            os.remove(name)


@skipUnless(iscommand("appstream-util"), "appstream-util not found")
class TQLAppDataFile(TestCase, _TAppDataFileMixin):
    PATH = os.path.join(QLDATA_DIR, "quodlibet.appdata.xml.in")


@skipUnless(iscommand("appstream-util"), "appstream-util not found")
class TEFAppDataFile(TestCase, _TAppDataFileMixin):
    PATH = os.path.join(QLDATA_DIR, "exfalso.appdata.xml.in")
