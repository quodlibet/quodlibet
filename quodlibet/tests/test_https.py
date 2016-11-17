# -*- coding: utf-8 -*-
# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

import pytest
from gi.repository import Gio, Soup, GLib

from tests import TestCase, skipIf

from quodlibet.util import is_linux, is_osx, get_ca_file
from quodlibet.compat import urlopen, build_opener


@pytest.mark.network
@skipIf(is_linux(), "not on linux")
class Thttps(TestCase):
    """For Windows/OSX to check if we can create a TLS connection
    using both openssl and whatever backend soup/gio uses.
    """

    GOOD = ["https://sha256.badssl.com/"]
    BAD = [
        "https://expired.badssl.com/",
        "https://wrong.host.badssl.com/",
        "https://self-signed.badssl.com/",
    ]

    def test_urllib(self):
        for url in self.GOOD:
            urlopen(url, cafile=get_ca_file()).close()
        for url in self.BAD:
            with self.assertRaises(Exception):
                urlopen(url, cafile=get_ca_file()).close()

    def test_urllib_default(self):
        for url in self.GOOD:
            urlopen(url).close()
        for url in self.BAD:
            with self.assertRaises(Exception):
                urlopen(url).close()

    def test_urllib_build_opener(self):
        for url in self.GOOD:
            build_opener().open(url).close()
        for url in self.BAD:
            with self.assertRaises(Exception):
                build_opener().open(url).close()

    def test_gio(self):
        if is_osx():
            return

        for url in self.GOOD:
            client = Gio.SocketClient.new()
            client.set_tls(True)
            client.connect_to_uri(url, 443, None).close()

        for url in self.BAD:
            with self.assertRaises(GLib.GError):
                client = Gio.SocketClient.new()
                client.set_tls(True)
                client.connect_to_uri(url, 443, None).close()

    def test_soup(self):
        if is_osx():
            return

        for url in self.GOOD:
            session = Soup.Session.new()
            request = session.request_http("get", url)
            request.send(None).close()

        for url in self.BAD:
            with self.assertRaises(GLib.GError):
                session = Soup.Session.new()
                request = session.request_http("get", url)
                request.send(None).close()
