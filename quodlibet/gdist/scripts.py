# -*- coding: utf-8 -*-
# Copyright 2007 Joe Wreschnig
#           2015-2016 Christoph Reiter
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

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
