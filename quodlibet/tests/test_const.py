# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import subprocess

from tests import TestCase, add

from quodlibet import const
from quodlibet.util.path import is_fsnative


class Tconst(TestCase):

    def test_branch_name(self):
        devnull = open(os.devnull, 'w')
        try:
            subprocess.check_call(["hg", "status"], stdout=devnull)
        except (OSError, subprocess.CalledProcessError):
            # no active hg repo, skip
            return

        p = subprocess.Popen(["hg", "id", "-b"], stdout=subprocess.PIPE)
        branch = p.communicate()[0].strip()
        self.failIf(p.returncode)

        self.failUnlessEqual(branch, const.BRANCH_NAME)

    def test_path_types(self):
        self.assertTrue(is_fsnative(const.USERDIR))
        self.assertTrue(is_fsnative(const.HOME))
        self.assertTrue(is_fsnative(const.IMAGEDIR))
        self.assertTrue(is_fsnative(const.BASEDIR))

add(Tconst)
