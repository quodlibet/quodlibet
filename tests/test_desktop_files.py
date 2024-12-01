# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import subprocess

from tests import TestCase, mkstemp
from quodlibet import util


QLDATA_DIR = os.path.join(os.path.dirname(util.get_module_dir()), "data")


class _TDesktopFileMixin:
    PATH = None

    def test_filename(self):
        assert self.PATH.endswith(".desktop.in")

    def test_validate(self):
        with open(self.PATH, "rb") as template:
            desktop_data = template.read()

        # copy to a temp file and strip "_ from translatable entries
        fd, name = mkstemp(suffix=".desktop")
        os.close(fd)
        with open(name, "wb") as temp:
            new_lines = []
            for l in desktop_data.splitlines():
                if l.startswith(b"_"):
                    l = l[1:]
                new_lines.append(l)
            temp.write(b"\n".join(new_lines))

        # pass to desktop-file-validate
        try:
            output = subprocess.check_output(
                ["desktop-file-validate", name], stderr=subprocess.STDOUT)
        except OSError:
            # desktop-file-validate not available
            return
        except subprocess.CalledProcessError as e:
            output = e.output
        finally:
            os.remove(name)

        if output:
            raise Exception(output)


class TQLDesktopFile(TestCase, _TDesktopFileMixin):
    PATH = os.path.join(QLDATA_DIR, "io.github.quodlibet.QuodLibet.desktop.in")


class TEFDesktopFile(TestCase, _TDesktopFileMixin):
    PATH = os.path.join(QLDATA_DIR, "io.github.quodlibet.ExFalso.desktop.in")
