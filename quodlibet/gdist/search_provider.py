# Copyright 2013 Christoph Reiter
#
# This software and accompanying documentation, if any, may be freely
# used, distributed, and/or modified, in any form and for any purpose,
# as long as this notice is preserved. There is no warranty, either
# express or implied, for this software.

import os

from distutils.util import change_root
from distutils.core import Command


class install_search_provider(Command):

    user_options = []
    root = None
    prefix = None
    search_provider = None

    def initialize_options(self):
        pass

    def finalize_options(self):
        self.set_undefined_options('install',
                                   ('root', 'root'),
                                   ('install_base', 'prefix'))

        self.search_provider = self.distribution.search_provider

    def run(self):
        basepath = os.path.join(
            self.prefix, 'share', 'gnome-shell', 'search-providers')
        if self.root is not None:
            basepath = change_root(self.root, basepath)

        self.mkpath(basepath)
        self.copy_file(self.search_provider, basepath)
