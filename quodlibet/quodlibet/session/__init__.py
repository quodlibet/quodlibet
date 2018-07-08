# -*- coding: utf-8 -*-
# Copyright 2018 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import print_d
from ._base import SessionClient, SessionError


def init(app):
    """Returns an active SessionClient instance or None"""

    from .gnome import GnomeSessionClient

    client = GnomeSessionClient()
    try:
        client.open(app)
    except SessionError as e:
        print_d(str(e))
    else:
        return client

    return SessionClient()
