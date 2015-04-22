# -*- coding: utf-8 -*-
# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import sys

from quodlibet import windows


if os.name == "nt":
    environ = windows.WindowsEnviron()
else:
    environ = os.environ
"""
An environ dict which contains unicode under Windows and str everywhere else
"""


if os.name == "nt":
    argv = windows.get_win32_unicode_argv()
else:
    argv = sys.argv
"""
An argv list which contains unicode under Windows and str everywhere else
"""
