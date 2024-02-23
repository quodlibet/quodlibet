# Copyright 2013-2016 Christoph Reiter
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


class BuildDbusServices(Command):
    """Build .service files"""

    description = "build .service files"
    user_options = []

    def initialize_options(self):
        self.build_base = None
        self.dbus_services = None

    def finalize_options(self):
        self.dbus_services = self.distribution.dbus_services
        self.set_undefined_options("build", ("build_base", "build_base"))

    def run(self):
        basepath = os.path.join(self.build_base, "share", "dbus-1", "services")
        self.mkpath(basepath)
        for service in self.dbus_services:
            in_variant = service + ".in"
            target_path = os.path.join(basepath, os.path.basename(service))
            if os.path.exists(in_variant):
                # the exec line needs the install path, so we can't really
                # do anything here besides renaming
                self.copy_file(in_variant, target_path)
            else:
                self.copy_file(service, target_path)


def _replace(path, pattern, subst):
    with open(path, "rb") as hi:
        data = hi.read()
        with open(path, "wb") as ho:
            ho.write(data.replace(pattern, subst))


class InstallDbusServices(Command):
    """Install .service files"""

    description = "install .service files"
    user_options = []

    def initialize_options(self):
        self.install_dir = None
        self.exec_prefix = None
        self.skip_build = None
        self.dbus_services = None
        self.build_base = None
        self.outfiles = []

    def finalize_options(self):
        self.set_undefined_options(
            "build",
            ("build_base", "build_base"))

        self.set_undefined_options(
            "install",
            ("install_data", "install_dir"),
            ("exec_prefix", "exec_prefix"),
            ("skip_build", "skip_build"))

        self.set_undefined_options(
            "build_dbus_services",
            ("dbus_services", "dbus_services"))

    def get_outputs(self):
        return self.outfiles

    def run(self):
        if not self.skip_build:
            self.run_command("build_dbus_services")

        basepath = os.path.join(
            self.install_dir, "share", "dbus-1", "services")
        out = self.mkpath(basepath)
        self.outfiles.extend(out or [])

        srcpath = os.path.join(self.build_base, "share", "dbus-1", "services")
        for service in self.dbus_services:
            service_name = os.path.basename(service)
            fullsrc = os.path.join(srcpath, service_name)
            fullpath = os.path.join(basepath, service_name)
            (out, _) = self.copy_file(fullsrc, fullpath)
            self.outfiles.append(out)
            prefix = self.exec_prefix or ""
            if not isinstance(prefix, bytes):
                prefix = prefix.encode("utf-8")
            _replace(fullpath, b"@PREFIX@", prefix)


__all__ = ["BuildDbusServices", "InstallDbusServices"]
