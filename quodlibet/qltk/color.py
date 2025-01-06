# Copyright 2020 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gdk


def mix(src: Gdk.RGBA, dest: Gdk.RGBA, ratio: float) -> Gdk.RGBA:
    """Mixes two Gdk colours into a result"""
    ratio = min(1.0, max(0.0, ratio))
    inv = 1.0 - ratio
    return Gdk.RGBA(
        inv * src.red + ratio * dest.red,
        inv * src.green + ratio * dest.green,
        inv * src.blue + ratio * dest.blue,
        inv * src.alpha + ratio * dest.alpha,
    )
