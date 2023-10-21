# Copyright 2018 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import print_d
from ._base import SessionClient, SessionError


class XSMPSessionClient(SessionClient):

    def __init__(self):
        super().__init__()
        self._client = None

    def open(self, app):
        try:
            from ._xsmp import XSMPClient, XSMPError
        except ImportError as e:
            raise SessionError(e) from e

        print_d("Connecting with XSMP")
        client = XSMPClient()
        try:
            client.open()
        except XSMPError as e:
            raise SessionError(e) from e

        try:
            from gi.repository import GdkX11
        except ImportError:
            pass
        else:
            GdkX11.x11_set_sm_client_id(client.client_id)

        print_d("Connected. Client ID: %s" % client.client_id)

        def save_yourself(client, *args):
            print_d("xsmp: save_yourself %r" % (args,))
            client.save_yourself_done(True)

        def die(client, *args):
            print_d("xsmp: die")
            app.quit()

        def save_complete(client):
            print_d("xsmp: save_complete")

        def shutdown_cancelled(client):
            print_d("xsmp: shutdown_cancelled")

        client.connect("save-yourself", save_yourself)
        client.connect("die", die)
        client.connect("save-complete", save_complete)
        client.connect("shutdown-cancelled", shutdown_cancelled)
        self._client = client

    def close(self):
        if self._client is None:
            return

        print_d("Disconnecting from XSMP")
        self._client.close()
        self._client = None
