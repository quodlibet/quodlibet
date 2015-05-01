# -*- coding: utf-8 -*-
# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

"""Varisour function for figuring out which platform wa are running on
and under which environment.
"""

import os


def is_unity():
    """If we are running under Ubuntu/Unity"""

    return "Unity" in os.environ.get("XDG_CURRENT_DESKTOP", "")
