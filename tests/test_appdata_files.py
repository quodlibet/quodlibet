# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import re
import subprocess
import functools

from quodlibet import util

from tests import TestCase, skipIf


QLDATA_DIR = os.path.join(os.path.dirname(util.get_module_dir()), "data")


@functools.lru_cache
def get_appstream_cli_version():
    try:
        result = subprocess.run(
            ["appstreamcli", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        data = result.stdout
    except FileNotFoundError:
        return (0, 0, 0)

    text = data.decode("utf-8", "replace")
    # The first line is like "AppStream version: 1.0.3"; later lines can list
    # compiled-against paths (e.g. a Nix glibc store path) that the old
    # last-token parsing choked on. Grab the first version-like number.
    match = re.search(r"\d+\.\d+(?:\.\d+)*", text)
    if match is None:
        return (0, 0, 0)
    return tuple(int(p) for p in match.group(0).split("."))


def is_too_old_appstream_cli_version():
    return get_appstream_cli_version() < (0, 12, 0)


class _TAppDataFileMixin:
    PATH = None

    def test_filename(self):
        assert self.PATH.endswith(".appdata.xml.in")

    def test_validate(self):
        try:
            subprocess.check_output(
                ["appstreamcli", "validate", "--no-net", self.PATH],
                stderr=subprocess.STDOUT,
            )
        except subprocess.CalledProcessError as e:
            raise Exception(e.output) from e


@skipIf(is_too_old_appstream_cli_version(), "appstreamcli is too old")
class TQLAppDataFile(TestCase, _TAppDataFileMixin):
    PATH = os.path.join(QLDATA_DIR, "io.github.quodlibet.QuodLibet.appdata.xml.in")


@skipIf(is_too_old_appstream_cli_version(), "appstreamcli is too old")
class TEFAppDataFile(TestCase, _TAppDataFileMixin):
    PATH = os.path.join(QLDATA_DIR, "io.github.quodlibet.ExFalso.appdata.xml.in")
