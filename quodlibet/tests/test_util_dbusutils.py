# -*- coding: utf-8 -*-
# Copyright 2012 Christoph Reiter <christoph.reiter@gmx.at>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

from tests import TestCase, add

import dbus
from quodlibet.util.dbusutils import apply_signature


class TDbusUtils(TestCase):
    def test_scale(self):
        value = apply_signature(2, "u")
        self.failUnless(isinstance(value, dbus.UInt32))

        value = apply_signature({"a": "b"}, "a{ss}")
        self.failUnlessEqual(value.signature, "ss")
        self.failUnless(isinstance(value, dbus.Dictionary))

        value = apply_signature(("a",), "a(s)")
        self.failUnlessEqual(value.signature, "s")
        self.failUnless(isinstance(value, dbus.Struct))

        value = apply_signature(("a", "b"), "as")
        self.failUnlessEqual(value.signature, "s")
        self.failUnless(isinstance(value, dbus.Array))

        self.failUnlessRaises(TypeError, apply_signature, 2, "a(s)")

        text = '\xc3\xb6\xc3\xa4\xc3\xbc'
        value = apply_signature(text, "s", utf8_strings=True)
        self.failUnless(isinstance(value, str))
        value = apply_signature(text, "s")
        self.failUnless(isinstance(value, unicode))

        text = u"öäü"
        value = apply_signature(text, "s", utf8_strings=True)
        self.failUnless(isinstance(value, str))
        value = apply_signature(text, "s")
        self.failUnless(isinstance(value, unicode))

add(TDbusUtils)
