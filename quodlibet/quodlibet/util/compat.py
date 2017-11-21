# -*- coding: utf-8 -*-
# Copyright (C) 2015  Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys


PY2 = sys.version_info[0] == 2
PY3 = not PY2


if PY2:
    text_type = unicode
else:
    text_type = str
