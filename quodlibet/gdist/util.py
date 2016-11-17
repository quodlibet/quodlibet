# -*- coding: utf-8 -*-
# Copyright 2016 Christoph Reiter
#
# This software and accompanying documentation, if any, may be freely
# used, distributed, and/or modified, in any form and for any purpose,
# as long as this notice is preserved. There is no warranty, either
# express or implied, for this software.

from distutils.core import Distribution
from distutils.core import Command


def get_dist_class(name):
    # in case of setuptools this returns the extended commands
    return Distribution({}).get_command_class(name)


Distribution, Command, get_dist_class
