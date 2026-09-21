# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Ubuntu Unity integration (quicklist).

Disabled under GTK4: Dbusmenu/Unity are GTK3-only and conflict with GTK4's
type system. The MPRIS plugin covers sound menu integration on modern
desktops.
"""

is_unity = False


def init(desktop_id, player):
    """No-op under GTK4."""
    return
