# -*- coding: utf-8 -*-
# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

import os

from tests import TestCase, skipUnless

from gi.repository import Gio, Soup

from quodlibet.util import is_osx, is_windows
from quodlibet.compat import urlopen


# this is fixed in 3.6, but we currently still use 3.5 bundles on travis
if is_osx():
    glib_net_fixed = "GTLS_SYSTEM_CA_FILE" in os.environ
else:
    glib_net_fixed = True


@skipUnless(is_osx() or is_windows())
class Thttps(TestCase):
    """For Windows/OSX to check if we can create a TLS connection
    using both openssl and whatever backend soup/gio uses.
    """

    URI = "https://www.google.com"

    def test_urllib(self):
        if is_windows():
            # FXIME
            return
        urlopen(self.URI).close()

    def test_gio(self):
        if not glib_net_fixed:
            return
        client = Gio.SocketClient.new()
        client.set_tls(True)
        client.connect_to_uri(self.URI, 443, None).close()

    def test_soup(self):
        if not glib_net_fixed:
            return
        session = Soup.Session.new()
        request = session.request_http("get", self.URI)
        request.send(None).close()
