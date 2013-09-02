# Copyright 2013 Christoph Reiter
#
# This software and accompanying documentation, if any, may be freely
# used, distributed, and/or modified, in any form and for any purpose,
# as long as this notice is preserved. There is no warranty, either
# express or implied, for this software.

import os

from distutils.util import change_root
from distutils.core import Command


class build_dbus_services(Command):
    """Build .service files"""

    description = "build .service files"
    user_options = []

    def initialize_options(self):
        self.build_base = None

    def finalize_options(self):
        self.dbus_services = self.distribution.dbus_services
        self.set_undefined_options('build', ('build_base', 'build_base'))

    def run(self):
        basepath = os.path.join(self.build_base, 'share', 'dbus-1', 'services')
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


class install_dbus_services(Command):
    """Install .service files"""

    description = "install .service files"
    user_options = []

    def initialize_options(self):
        self.prefix = None
        self.skip_build = None
        self.dbus_services = None
        self.build_base = None
        self.root = None

    def finalize_options(self):
        self.set_undefined_options(
            'build',
            ('build_base', 'build_base'))

        self.set_undefined_options(
            'install',
            ('root', 'root'),
            ('install_base', 'prefix'),
            ('skip_build', 'skip_build'))

        self.set_undefined_options(
            'build_dbus_services',
            ('dbus_services', 'dbus_services'))

    def run(self):
        if not self.skip_build:
            self.run_command('build_dbus_services')

        basepath = os.path.join(self.prefix, 'share', 'dbus-1', 'services')
        if self.root is not None:
            basepath = change_root(self.root, basepath)
        self.mkpath(basepath)

        srcpath = os.path.join(self.build_base, 'share', 'dbus-1', 'services')
        for service in self.dbus_services:
            service_name = os.path.basename(service)
            fullsrc = os.path.join(srcpath, service_name)
            fullpath = os.path.join(basepath, service_name)
            self.copy_file(fullsrc, fullpath)
            _replace(fullpath, "@PREFIX@", self.prefix)


__all__ = ["build_dbus_services", "install_dbus_services"]
