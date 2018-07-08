# -*- coding: utf-8 -*-
# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase, init_fake_app, destroy_fake_app

from quodlibet import session


class TSession(TestCase):

    def setUp(self):
        init_fake_app()

    def tearDown(self):
        destroy_fake_app()

    def test_session(self):
        from quodlibet import app

        client = session.init(app)
        if client is None:
            client.close()
