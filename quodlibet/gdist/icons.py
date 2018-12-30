# Copyright 2012-2016 Christoph Reiter
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
import subprocess

from .util import Command


def update_icon_cache(*args):
    args = list(args)
    try:
        subprocess.check_call(
            ['gtk-update-icon-cache-3.0'] + args)
    except OSError:
        try:
            subprocess.check_call(
                ['gtk-update-icon-cache'] + args)
        except OSError:
            return False
        except subprocess.CalledProcessError:
            return False
    except subprocess.CalledProcessError:
        return False
    return True


class install_icons(Command):
    """Copy app icons to hicolor/pixmaps and update the global cache"""

    user_options = []

    def initialize_options(self):
        self.install_dir = None
        self.outfiles = []

    def finalize_options(self):
        self.set_undefined_options('install',
                                   ('install_data', 'install_dir'))

    def get_outputs(self):
        return self.outfiles

    def run(self):
        # install into hicolor icon theme
        basepath = os.path.join(self.install_dir, 'share', 'icons', 'hicolor')

        local = os.path.join("quodlibet", "images", "hicolor")

        # copy all "apps" images
        for entry in os.listdir(local):
            source = os.path.join(local, entry, "apps")
            dest = os.path.join(basepath, entry, "apps")
            out = self.mkpath(dest)
            self.outfiles.extend(out or [])

            for image in os.listdir(source):
                if os.path.splitext(image)[-1] in (".png", ".svg"):
                    file_path = os.path.join(source, image)
                    (out, _) = self.copy_file(file_path, dest)
                    self.outfiles.append(out)

        # this fails during packaging.. so ignore the outcome
        update_icon_cache(basepath)
