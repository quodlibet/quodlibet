# Copyright 2007-2008 Joe Wreschnig
#           2009,2012-2016 Christoph Reiter
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

"""install man pages

Commands to install Unix man pages.
"""

import os

from .util import Command


class InstallMan(Command):
    """install man pages

    Install man pages into $prefix/share/man/manN
    or into $mandir/manN by using setup.py install --mandir=$mandir
    """

    description = "install man pages"
    user_options = []

    def initialize_options(self):
        self.man_pages = None
        self.mandir = None
        self.install_dir = None
        self.outfiles = []

    def finalize_options(self):
        self.set_undefined_options(
            "install",
            ("install_data", "install_dir"),
            ("mandir", "mandir"),
        )

        if self.mandir is None:
            self.mandir = os.path.join(self.install_dir, "share", "man")

        self.man_pages = self.distribution.man_pages
        for man_page in self.man_pages:
            if not man_page[-1].isdigit():
                raise SystemExit("%r has no section" % man_page)

    def get_outputs(self):
        return self.outfiles

    def run(self):
        basepath = self.mandir
        out = self.mkpath(basepath)
        self.outfiles.extend(out or [])

        for man_page in self.man_pages:
            manpath = os.path.join(basepath, "man" + man_page[-1])
            out = self.mkpath(manpath)
            self.outfiles.extend(out or [])
            fullpath = os.path.join(manpath, os.path.basename(man_page))
            (out, _) = self.copy_file(man_page, fullpath)
            self.outfiles.append(out)


__all__ = ["InstallMan"]
