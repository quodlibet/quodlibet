# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import subprocess

from tests import TestCase, add, mkstemp


QLDATA_DIR = os.path.join(os.path.dirname(
    os.path.dirname(os.path.realpath(__file__))), "data")


class _TAppDataFile(TestCase):
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
            temp.write(header + "\n")
            temp.write(ElementTree.tostring(tree.getroot(), encoding="utf-8"))

        # pass to desktop-file-validate
        try:
            subprocess.check_output(
                ["appdata-validate", "--nonet", name],
                stderr=subprocess.STDOUT)
        except OSError:
            # appdata-validate not available
            return
        except subprocess.CalledProcessError as e:
            raise Exception(e.output)
        finally:
            os.remove(name)


class TQLAppDataFile(_TAppDataFile):
    PATH = os.path.join(QLDATA_DIR, "quodlibet.appdata.xml.in")

add(TQLAppDataFile)


class TEFAppDataFile(_TAppDataFile):
    PATH = os.path.join(QLDATA_DIR, "exfalso.appdata.xml.in")

add(TEFAppDataFile)
