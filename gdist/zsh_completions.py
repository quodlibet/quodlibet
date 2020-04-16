# Copyright 2016 Christoph Reiter
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

from .util import Command


class install_zsh_completions(Command):

    user_options = []

    def initialize_options(self):
        self.install_dir = None
        self.zsh_completions = []
        self.outfiles = []

    def finalize_options(self):
        self.set_undefined_options('install',
                                   ('install_data', 'install_dir'))

        self.zsh_completions = self.distribution.zsh_completions

    def get_outputs(self):
        return self.outfiles

    def run(self):
        basepath = os.path.join(
            self.install_dir, 'share', 'zsh', 'site-functions')
        out = self.mkpath(basepath)
        self.outfiles.extend(out or [])
        for src, dest in self.zsh_completions:
            (out, _) = self.copy_file(src, os.path.join(basepath, dest))
            self.outfiles.append(out)
