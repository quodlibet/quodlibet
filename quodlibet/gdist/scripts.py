# -*- coding: utf-8 -*-
# Copyright 2007 Joe Wreschnig
#
# This software and accompanying documentation, if any, may be freely
# used, distributed, and/or modified, in any form and for any purpose,
# as long as this notice is preserved. There is no warranty, either
# express or implied, for this software.

import os

from .util import get_dist_class


du_build_scripts = get_dist_class("build_scripts")


class build_scripts(du_build_scripts):
    description = "copy scripts to build directory"

    def run(self):
        du_build_scripts.run(self)

        # remove ".py"
        for script in self.scripts:
            outfile = os.path.join(self.build_dir, os.path.basename(script))
            new = os.path.splitext(outfile)[0]
            try:
                os.unlink(new)
            except OSError:
                pass
            self.move_file(outfile, new)
