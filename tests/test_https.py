# Copyright 2016 Christoph Reiter
#           2023 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
import os

import pytest
from gi.repository import Gio, Soup, GLib

from urllib.request import urlopen, build_opener
from tests import TestCase, skipIf

from quodlibet.util import is_linux


@pytest.mark.network
# See https://stackoverflow.com/questions/75274925
@skipIf(is_linux() and not os.environ.get("container"), "Only on Flatpak linux")
class Thttps(TestCase):
    """For Windows/OSX/Flatpak to check if we can create a TLS connection
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
            urlopen(url).close()
        for url in self.BAD:
            with pytest.raises(OSError):
                urlopen(url).close()

    def test_urllib_default(self):
        for url in self.GOOD:
            urlopen(url).close()
        for url in self.BAD:
            with pytest.raises(OSError):
                urlopen(url).close()

    def test_urllib_build_opener(self):
        for url in self.GOOD:
            build_opener().open(url).close()
        for url in self.BAD:
            with pytest.raises(OSError):
                build_opener().open(url).close()

    def test_gio(self):
        for url in self.GOOD:
            client = Gio.SocketClient()
            client.set_tls(True)
            client.connect_to_uri(url, 443, None).close()

        for url in self.BAD:
            with pytest.raises(GLib.GError):
                client = Gio.SocketClient()
                client.set_tls(True)
                client.connect_to_uri(url, 443, None).close()

    def test_soup(self):
        for url in self.GOOD:
            session = Soup.Session()
            msg = Soup.Message.new("GET", url)
            session.send_and_read(msg)

        for url in self.BAD:
            with pytest.raises(GLib.GError):
                session = Soup.Session()
                msg = Soup.Message.new("GET", url)
                session.send_and_read(msg)
