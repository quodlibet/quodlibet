# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import xml.etree.ElementTree as ET

import dbus
import dbus.service


def dbus_unicode_validate(text):
    """Takes a unicode string and replaces all invalid codepoints that would
    lead to errors if passed to dbus"""

    if isinstance(text, str):
        text = text.decode("utf-8")

    # https://bugs.freedesktop.org/show_bug.cgi?id=40817
    def valid(c):
        return (c < 0x110000 and
                (c & 0xFFFFF800) != 0xD800 and
                (c < 0xFDD0 or c > 0xFDEF) and
                (c & 0xFFFE) != 0xFFFE)

    cps = []
    for c in map(ord, text):
        if valid(c):
            cps.append(c)
        else:
            cps.append(0xFFFD)
    return u"".join(map(unichr, cps))


def list_spec_properties(spec):
    """Parse a property spec and return a dict:

    {'Metadata': {'access': 'read', 'type': 'a{sv}', 'emit': 'true'}

    'access' can be: read/write/readwrite
    'type' is the dbus data type (dbus.Signature instance)
    'emit' can be true/false/invalidates (see dbus spec)
    """

    ANNOTATION_EMITS = "org.freedesktop.DBus.Property.EmitsChangedSignal"

    def get_emit(element, fallback):
        for anno in element.findall("annotation"):
            if anno.attrib["name"] == ANNOTATION_EMITS:
                emit = anno.attrib["value"]
                break
        else:
            emit = fallback
        return emit

    root = ET.fromstring('<?xml version="1.0"?><props>' + spec + '</props>')
    props = {}
    root_emit = get_emit(root, "true")
    for element in root:
        if element.tag != "property":
            continue

        attrs = element.attrib
        attrs["emit"] = get_emit(element, root_emit)
        attrs["type"] = dbus.Signature(attrs["type"])
        props[attrs.pop("name")] = attrs

    return props


def filter_property_spec(spec, wl=None, bl=None):
    """Remove properties based on a white list or black list."""

    if wl and bl:
        raise ValueError
    if not wl and not bl:
        return spec
    root = ET.fromstring('<?xml version="1.0"?><props>' + spec + '</props>')
    if wl:
        to_rm = lambda e: e.attrib["name"] not in wl
    elif bl:
        to_rm = lambda e: e.attrib["name"] in bl
    strs = []
    for element in root:
        if element.tag != "property" or not to_rm(element):
            strs.append(ET.tostring(element).strip())
    return "\n".join(strs)


TYPE_MAP = {
    "b": dbus.Boolean,
    "n": dbus.Int16,
    "i": dbus.Int32,
    "x": dbus.Int64,
    "q": dbus.UInt16,
    "u": dbus.UInt32,
    "t": dbus.UInt64,
    "d": dbus.Double,
    "o": dbus.ObjectPath,
    "g": dbus.Signature,
    "s": dbus.String,
    "v": lambda x: x,
}


def apply_signature(value, sig, utf8_strings=False):
    """Casts basic types to the right dbus types and packs them
    into containers with the right signature, so they get validated on
    sending."""

    # dbus properties are variant, but have a signature defined, so
    # we have to convert manually here.

    if utf8_strings and sig == "s":
        return dbus.UTF8String(value)
    elif sig in TYPE_MAP:
        return TYPE_MAP[sig](value)
    elif sig.startswith("a{"):
        return dbus.Dictionary(value, signature=sig[2:-1])
    elif sig.startswith("a("):
        return dbus.Struct(value, signature=sig[2:-1])
    elif sig.startswith("a"):
        return dbus.Array(value, signature=sig[1:])
    elif utf8_strings and sig == "s":
        return dbus.UTF8String(value)
    else:
        return TYPE_MAP[sig](value)

    # Unknown type, just return as is
    return value


class DBusIntrospectable(object):
    """Simply collects all introspection data from other mixins
    and provides the Introspect DBus method returning all combined.

    All classes need to call set_introspection with their interface
    and provided signals, properties, methods in the introspection
    xml format.

    The dbus bindings allready provide a Introspect method, but it doesn't
    understand properties, also having them in text format in the class
    is a nice documentation.
    """

    IFACE = "org.freedesktop.DBus.Introspectable"
    ISPEC = """
<method name="Introspect">
    <arg type="s" name="xml_data" direction="out"/>
</method>
"""

    def __init__(self):
        self.__ispec = {}
        self.set_introspection(DBusIntrospectable.IFACE,
                               DBusIntrospectable.ISPEC)

    def set_introspection(self, interface, introspection):
        self.__ispec.setdefault(interface, []).append(introspection)

    @dbus.service.method(IFACE)
    def Introspect(self):
        parts = []
        parts.append("<node>")
        for iface, intros in self.__ispec.iteritems():
            parts.append("<interface name=\"%s\">" % iface)
            parts.extend(intros)
            parts.append("</interface>")
        parts.append("</node>")
        return "\n".join(parts)


class DBusProperty(object):
    """A mixin for dbus.Object classes to support dbus properties.

    Register properties by passing the XML introspection to
    'set_properties'.

    The class needs to provide 'get/set_property'.

    In case the base Object is a FallbackObject, 'get/set_property' also
    need to handle an additional realtive path parameter.

    Whenever a property changes, 'emit_properties_changed' needs to be
    called (except if the annotations disable it). In case of
    FallbackObject, with a relative path to the real object (defaults to
    the main one).
    """

    IFACE = "org.freedesktop.DBus.Properties"
    ISPEC = """
<method name="Get">
    <arg type="s" name="interface_name" direction="in"/>
    <arg type="s" name="property_name" direction="in"/>
    <arg type="v" name="value" direction="out"/>
</method>
<method name="GetAll">
    <arg type="s" name="interface_name" direction="in"/>
    <arg type="a{sv}" name="properties" direction="out"/>
</method>
<method name="Set">
    <arg type="s" name="interface_name" direction="in"/>
    <arg type="s" name="property_name" direction="in"/>
    <arg type="v" name="value" direction="in"/>
</method>
<signal name="PropertiesChanged">
    <arg type="s" name="interface_name"/>
    <arg type="a{sv}" name="changed_properties"/>
    <arg type="as" name="invalidated_properties"/>
</signal>"""

    def __init__(self):
        self.__props = {}
        self.__impl = {}
        self.set_introspection(DBusProperty.IFACE, DBusProperty.ISPEC)

    def set_properties(self, interface, ispec, bl=None, wl=None):
        """Register properties and set instrospection for the given
        property spec. Provide a black list or white list, for
        optional, not implemented properties."""

        ispec = filter_property_spec(ispec, wl=wl, bl=bl)
        self.__props[interface] = list_spec_properties(ispec)
        self.__impl.setdefault(interface, [])
        self.set_introspection(interface, ispec)

    def get_properties(self, interface):
        """Returns a list of (interface, property) for all properties of
        the specified interface and subinterfaces"""

        result = [(interface, p) for p in self.__props[interface].keys()]
        for sub in self.__impl[interface]:
            result.extend(self.get_properties(sub))
        return result

    def get_value(self, interface, prop, path="/"):
        """Returns the value of a property"""

        interface = self.get_interface(interface, prop)
        if self.SUPPORTS_MULTIPLE_OBJECT_PATHS:
            value = self.get_property(interface, prop, path)
        else:
            value = self.get_property(interface, prop)

        prop_sig = self.__props[interface][prop]["type"]
        return apply_signature(value, prop_sig)

    def get_interface(self, interface, prop):
        """Returns the real interface that implements the property"""

        if prop in self.__props[interface]:
            return interface
        for sub in self.__impl[interface]:
            if self.get_interface(sub, prop):
                return sub

    def implement_interface(self, iface, sub_iface):
        """Set a sub interface. All actions on that interface
        will check the sub interface in case the property is not
        found."""

        self.__props.setdefault(iface, {})
        self.__props.setdefault(sub_iface, {})
        self.__impl.setdefault(iface, []).append(sub_iface)

    def emit_properties_changed(self, interface, properties, path="/"):
        """Emits PropertiesChanged for the specified properties"""

        combos = {}
        for prop in properties:
            iface = self.get_interface(interface, prop)
            if iface is None:
                raise ValueError("Property %s not registered" % prop)
            combos.setdefault(iface, []).append(prop)

        for iface, props in combos.iteritems():
            values = {}
            inval = []
            for prop in props:
                emit = self.__props[iface][prop]["emit"]
                if emit == "false":
                    raise ValueError("Can't emit changed signal for %s" % prop)
                elif emit == "true":
                    values[prop] = self.get_value(iface, prop, path)
                elif emit == "invalidates":
                    inval.append(prop)

            if self.SUPPORTS_MULTIPLE_OBJECT_PATHS:
                self.PropertiesChanged(iface, values, inval, rel=path)
            else:
                self.PropertiesChanged(iface, values, inval)

    @dbus.service.method(dbus_interface=IFACE, in_signature="ss",
                         out_signature="v", rel_path_keyword="path")
    def Get(self, interface, prop, path):
        return self.get_value(interface, prop, path)

    @dbus.service.method(dbus_interface=IFACE, in_signature="ssv",
                         out_signature="", rel_path_keyword="path")
    def Set(self, interface, prop, value, path):
        interface = self.get_interface(interface, prop)
        if self.SUPPORTS_MULTIPLE_OBJECT_PATHS:
            self.set_property(interface, prop, value, path)
        else:
            self.set_property(interface, prop, value)

    @dbus.service.method(dbus_interface=IFACE, in_signature="s",
                         out_signature="a{sv}", rel_path_keyword="path")
    def GetAll(self, interface, path):
        values = {}
        for iface, prop in self.get_properties(interface):
            values[prop] = self.get_value(iface, prop, path)
        return values

    @dbus.service.signal(IFACE, signature="sa{sv}as", rel_path_keyword="rel")
    def PropertiesChanged(self, interface, changed, invalidated, rel=""):
        pass
