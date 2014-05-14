# Copyright 2014 Christoph Reiter <reiter.christoph@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

from gi.repository import Gtk

from quodlibet.plugins.events import EventPlugin
from quodlibet import app

from .main import MPDServer
from .tcpserver import ServerError


class MPDServerPlugin(EventPlugin):
    PLUGIN_ID = "mpd_server"
    PLUGIN_NAME = _("MPD Server")
    PLUGIN_DESC = _("Provides a MPD server interface")
    PLUGIN_ICON = Gtk.STOCK_CONNECT

    PORT = 6600

    def enabled(self):
        self.server = MPDServer(app, self.PORT)
        try:
            self.server.start()
        except ServerError as e:
            print_w(str(e))

    def disabled(self):
        self.server.stop()
        del self.server
