# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import subprocess

from tests import TestCase, add

from quodlibet import const


class Tconst(TestCase):

    def test_branch_name(self):
        devnull = open(os.devnull, 'w')
        try:
            subprocess.check_call(["hg", "version"], stdout=devnull)
        except OSError:
            # no active hg repo, skip
            return

        p = subprocess.Popen(["hg", "id", "-b"], stdout=subprocess.PIPE)
        branch = p.communicate()[0].strip()
        self.failIf(p.returncode)

        self.failUnlessEqual(branch, const.BRANCH_NAME)

add(Tconst)
