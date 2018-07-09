# -*- coding: utf-8 -*-
# Copyright 2018 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from .gnome import GnomeSessionClient


class XfceSessionClient(GnomeSessionClient):

    DBUS_NAME = 'org.xfce.SessionManager'
    DBUS_OBJECT_PATH = '/org/xfce/SessionManager'
    DBUS_MAIN_INTERFACE = 'org.xfce.Session.Manager'
    DBUS_CLIENT_INTERFACE = 'org.xfce.Session.Client'
