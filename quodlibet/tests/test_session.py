# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase, init_fake_app, destroy_fake_app

from quodlibet import app
from quodlibet import session
from quodlibet.session import SessionError, iter_backends


class TSession(TestCase):

    def setUp(self):
        init_fake_app()

    def tearDown(self):
        destroy_fake_app()

    def test_session(self):
        client = session.init(app)
        client.close()

    def test_all(self):
        for backend in iter_backends():
            client = backend()
            try:
                client.open(app)
            except SessionError:
                pass
            else:
                client.close()
                client.close()
