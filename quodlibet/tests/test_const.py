# -*- coding: utf-8 -*-
# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import subprocess

from tests import TestCase

from quodlibet import const


class Tconst(TestCase):

    def test_branch_name(self):
        devnull = open(os.devnull, 'w')
        try:
            subprocess.check_call(["git", "status"], stdout=devnull)
        except (OSError, subprocess.CalledProcessError):
            # no active hg repo, skip
            return

        p = subprocess.Popen(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stdout=subprocess.PIPE)
        branch = p.communicate()[0].strip()
        self.failIf(p.returncode)

        # only check for stable/dev branches, no feature branches
        if branch == b"master" or branch.startswith(b"quodlibet"):
            branch = branch.decode("utf-8")
            self.failUnlessEqual(branch, const.BRANCH_NAME)
