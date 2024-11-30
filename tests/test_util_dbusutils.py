# Copyright 2012 Christoph Reiter <reiter.christoph@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase, skipUnless

try:
    import dbus
except ImportError:
    dbus = None
else:
    from quodlibet.util.dbusutils import apply_signature, list_spec_properties
    from quodlibet.util.dbusutils import filter_property_spec, DBusProperty
    from quodlibet.util.dbusutils import dbus_unicode_validate


ANN1 = """
<property name="Position" type="s" access="read">
<annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" \
value="false"/>
</property>
<property name="MinimumRate" type="s" access="read"/>
"""

ANN2 = """
<annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" \
value="false"/>
<property name="Foobar" type="s" access="read">
<annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" \
value="invalidates"/>
</property>
<property name="XXX" type="s" access="read"/>
"""


@skipUnless(dbus, "dbus missing")
class TDbusUtils(TestCase):

    def test_prop_sig(self):
        value = apply_signature(2, "u")
        assert isinstance(value, dbus.UInt32)

        value = apply_signature({"a": "b"}, "a{ss}")
        self.assertEqual(value.signature, "ss")
        assert isinstance(value, dbus.Dictionary)

        value = apply_signature(("a",), "a(s)")
        self.assertEqual(value.signature, "s")
        assert isinstance(value, dbus.Struct)

        value = apply_signature(("a", "b"), "as")
        self.assertEqual(value.signature, "s")
        assert isinstance(value, dbus.Array)

        self.assertRaises(TypeError, apply_signature, 2, "a(s)")

        text = b"\xc3\xb6\xc3\xa4\xc3\xbc"
        value = apply_signature(text, "s", utf8_strings=True)
        assert isinstance(value, str)
        value = apply_signature(text, "s")
        assert isinstance(value, str)

        text = "öäü"
        value = apply_signature(text, "s", utf8_strings=True)
        assert isinstance(value, str)
        value = apply_signature(text, "s")
        assert isinstance(value, str)

    def test_list_props(self):
        props = list_spec_properties(ANN1)
        self.assertEqual(props["Position"]["access"], "read")
        self.assertEqual(props["Position"]["emit"], "false")
        self.assertEqual(props["Position"]["type"], "s")

        self.assertEqual(props["MinimumRate"]["emit"], "true")

        props = list_spec_properties(ANN2)
        self.assertEqual(props["Foobar"]["emit"], "invalidates")
        self.assertEqual(props["XXX"]["emit"], "false")

    def test_filter_props(self):
        spec = filter_property_spec(ANN1, wl=["Position"])
        self.assertEqual(
            list(list_spec_properties(spec).keys()), ["Position"])
        props = list_spec_properties(spec)
        self.assertEqual(props["Position"]["emit"], "false")

        spec = filter_property_spec(ANN1, bl=["Position"])
        self.assertEqual(list(list_spec_properties(spec).keys()),
                             ["MinimumRate"])

        spec = filter_property_spec(ANN1)
        self.assertEqual(len(list_spec_properties(spec).keys()), 2)

    def test_validate_utf8(self):
        self.assertEqual(dbus_unicode_validate("X\ufffeX"), "X\ufffdX")
        self.assertEqual(dbus_unicode_validate(b"X\xef\xbf\xbeX"),
                             "X\ufffdX")

    def test_property_mixin(self):

        class X(DBusProperty):
            SUPPORTS_MULTIPLE_OBJECT_PATHS = False

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
        assert ("a1", "Position") in props
        assert ("a2", "XXX") in props
        props = x.get_properties("a2")
        assert ("a1", "Position") not in props

        self.assertEqual(x.get_interface("a2", "XXX"), "a2")
        self.assertEqual(x.get_interface("a1", "XXX"), "a2")

        self.assertEqual(x.get_value("a2", "XXX"), "a2")
        self.assertEqual(x.get_value("a1", "XXX"), "a2")
        self.assertEqual(x.get_value("a1", "Position"), "a1")
