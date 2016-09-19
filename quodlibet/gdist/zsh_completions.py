# -*- coding: utf-8 -*-
# Copyright 2016 Christoph Reiter
#
# This software and accompanying documentation, if any, may be freely
# used, distributed, and/or modified, in any form and for any purpose,
# as long as this notice is preserved. There is no warranty, either
# express or implied, for this software.

import os

from distutils.core import Command


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
            self.install_dir, 'share', 'zsh', 'vendor-completions')
        out = self.mkpath(basepath)
        self.outfiles.extend(out or [])
        for src, dest in self.zsh_completions:
            (out, _) = self.copy_file(src, os.path.join(basepath, dest))
            self.outfiles.append(out)
