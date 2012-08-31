# -*- coding: utf-8 -*-
# Copyright 2012 Christoph Reiter <christoph.reiter@gmx.at>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

from tests import TestCase, add

import dbus
from quodlibet.util.dbusutils import apply_signature, list_spec_properties
from quodlibet.util.dbusutils import filter_property_spec, DBusProperty
from quodlibet.util.dbusutils import dbus_unicode_validate, DBusIntrospectable


ANN1 = """
<property name="Position" type="s" access="read">
<annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="false"/>
</property>
<property name="MinimumRate" type="s" access="read"/>
"""

ANN2 = """
<annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="false"/>
<property name="Foobar" type="s" access="read">
<annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="invalidates"/>
</property>
<property name="XXX" type="s" access="read"/>
"""

class TDbusUtils(TestCase):
    def test_prop_sig(self):
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

    def test_list_props(self):
        props = list_spec_properties(ANN1)
        self.failUnlessEqual(props["Position"]["access"], "read")
        self.failUnlessEqual(props["Position"]["emit"], "false")
        self.failUnlessEqual(props["Position"]["type"], "s")

        self.failUnlessEqual(props["MinimumRate"]["emit"], "true")

        props = list_spec_properties(ANN2)
        self.failUnlessEqual(props["Foobar"]["emit"], "invalidates")
        self.failUnlessEqual(props["XXX"]["emit"], "false")

    def test_filter_props(self):
        spec = filter_property_spec(ANN1, wl=["Position"])
        self.failUnlessEqual(list_spec_properties(spec).keys(), ["Position"])
        props = list_spec_properties(spec)
        self.failUnlessEqual(props["Position"]["emit"], "false")

        spec = filter_property_spec(ANN1, bl=["Position"])
        self.failUnlessEqual(list_spec_properties(spec).keys(),
                             ["MinimumRate"])

        spec = filter_property_spec(ANN1)
        self.failUnlessEqual(len(list_spec_properties(spec).keys()), 2)

    def test_validate_utf8(self):
        self.failUnlessEqual(dbus_unicode_validate(u'X\ufffeX'), u"X\ufffdX")
        self.failUnlessEqual(dbus_unicode_validate('X\xef\xbf\xbeX'),
                             u"X\ufffdX")

    def test_property_mixin(self):
        class X(DBusProperty):
            SUPPORTS_MULTIPLE_OBJECT_PATHS=False
            def set_introspection(self, *args):
                pass
            def get_property(self, interface, name):
                return interface
            def set_property(self, interface, name, value):
                pass

        x = X()
        x.set_properties("a1", ANN1)
        x.set_properties("a2", ANN2)
        x.implement_interface("a1", "a2")

        props = x.get_properties("a1")
        self.failUnless(("a1", "Position") in props)
        self.failUnless(("a2", "XXX") in props)
        props = x.get_properties("a2")
        self.failIf(("a1", "Position") in props)

        self.failUnlessEqual(x.get_interface("a2", "XXX"), "a2")
        self.failUnlessEqual(x.get_interface("a1", "XXX"), "a2")

        self.failUnlessEqual(x.get_value("a2", "XXX"), "a2")
        self.failUnlessEqual(x.get_value("a1", "XXX"), "a2")
        self.failUnlessEqual(x.get_value("a1", "Position"), "a1")

add(TDbusUtils)
