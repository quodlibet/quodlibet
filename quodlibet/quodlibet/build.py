# -*- coding: utf-8 -*-
# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

"""This file gets edited at build time to add build specific data"""

BUILD_TYPE = u"default"
"""Either 'windows', 'windows-portable', 'osx-quodlibet',
'osx-exfalso' or 'default'"""

BUILD_INFO = u""
"""Additional build info like git revision etc"""

BUILD_VERSION = 0
"""1.2.3 with a BUILD_VERSION of 1 results in 1.2.3.1"""
