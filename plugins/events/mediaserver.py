# Copyright 2012 Christoph Reiter <christoph.reiter@gmx.at>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

import gtk

import dbus
import dbus.service
import dbus.glib

from quodlibet.plugins.events import EventPlugin
from quodlibet.parse import Pattern


class MediaServer(EventPlugin):
    PLUGIN_ID = "mediaserver"
    PLUGIN_NAME = _("UPnP AV Media Server")
    PLUGIN_DESC = _("Exposes all albums to the Rygel UPnP Media Server "
                    "through the MediaServer2 D-Bus interface")
    PLUGIN_ICON = gtk.STOCK_CONNECT
    PLUGIN_VERSION = "0.1"

    def enabled(self):
        from quodlibet.library import library

        entry = EntryObject()
        albums = AlbumsObject(entry, library)
        song = SongObject(library, [albums])

        self.objects = [entry, albums, song]

    def disabled(self):
        for obj in self.objects:
            obj.remove_from_connection()
        self.objects = []


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
        self.__ispec[interface] = introspection

    @dbus.service.method(IFACE)
    def Introspect(self):
        parts = []
        parts.append("<node>")
        for iface, intro in self.__ispec.iteritems():
            parts.append("<interface name=\"%s\">" % iface)
            parts.append(intro)
            parts.append("</interface>")
        parts.append("</node>")
        return "\n".join(parts)


class DBusProperty(object):
    """A mixin for dbus.Object classes to support dbus properties.

    Each property needs to be registered using register_property, and
    interfaces that implement other ones need to tell that by
    calling implement_interface.

    The class needs to provide get/set_property.

    In case the base Object is a FallbackObject, get/set also need to handle
    an additional realtive path parameter.

    Whenever a property changes emit_properties_changed/invalidated need
    to be called. In case of FallbackObject, with a relative path to
    the real object (defaults to the main one).
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

    def get_properties(self, interface):
        """Returns a list of (interface, property) for all properties of
        the specified interface and subinterfaces"""

        result = [(interface, p) for p in self.__props[interface]]
        for sub in self.__impl[interface]:
            result.extend(self.get_properties(sub))
        return result

    def get_value(self, interface, prop, path="/"):
        """Returns the value of a property"""
        interface = self.get_interface(interface, prop)
        if self.SUPPORTS_MULTIPLE_OBJECT_PATHS:
            return self.get_property(interface, prop, path)
        else:
            return self.get_property(interface, prop)

    def get_interface(self, interface, prop):
        """Returns the real interface that implements the property"""

        if prop in self.__props[interface]:
            return interface
        for sub in self.__impl[interface]:
            if self.get_interface(sub, prop):
                return sub

    def register_property(self, interface, name):
        """Register a property on an interface"""

        self.__props.setdefault(interface, []).append(name)
        self.__impl.setdefault(interface, [])

    def implement_interface(self, iface, sub_iface):
        """Set a sub interface. All actions on that interface
        will check the sub interface in case the property is not
        found."""

        self.__props.setdefault(iface, [])
        self.__props.setdefault(sub_iface, [])
        self.__impl.setdefault(iface, []).append(sub_iface)

    def emit_properties_changed(self, interface, props, path="/"):
        """Emits PropertiesChanged with the new values of the specified
        properties."""

        combos = {}
        for prop in props:
            iface = self.get_interface(interface, prop)
            combos.setdefault(iface, []).append(prop)

        for iface, props in combos.iteritems():
            new_values = {}
            for prop in props:
                if self.SUPPORTS_MULTIPLE_OBJECT_PATHS:
                    new_values[prop] = self.get_property(iface, prop, path)
                else:
                    new_values[prop] = self.get_property(iface, prop)

            if self.SUPPORTS_MULTIPLE_OBJECT_PATHS:
                self.PropertiesChanged(iface, new_values, [], rel=path)
            else:
                self.PropertiesChanged(iface, new_values, [])

    def emit_properties_invalidate(self, interface, props, path="/"):
        """Emits PropertiesChanged with a list of properties
        that are no longer valid and need to be updated."""

        combos = {}
        for prop in props:
            iface = self.get_interface(interface, prop)
            combos.setdefault(iface, []).append(prop)

        for iface, props in combos.iteritems():
            if self.SUPPORTS_MULTIPLE_OBJECT_PATHS:
                self.PropertiesChanged(iface, {}, [props], rel=path)
            else:
                self.PropertiesChanged(iface, {}, [props])

    @dbus.service.method(dbus_interface=IFACE, in_signature="ss",
                         out_signature="v", rel_path_keyword="path")
    def Get(self, interface, prop, path):
        interface = self.get_interface(interface, prop)
        if self.SUPPORTS_MULTIPLE_OBJECT_PATHS:
            return self.get_property(interface, prop, path)
        return self.get_property(interface, prop)

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
            if self.SUPPORTS_MULTIPLE_OBJECT_PATHS:
                values[prop] = self.get_property(iface, prop, path)
            else:
                values[prop] = self.get_property(iface, prop)
        return values

    @dbus.service.signal(IFACE, signature="sa{sv}as", rel_path_keyword="rel")
    def PropertiesChanged(self, interface, changed, invalidated, rel=""):
        pass


class DBusPropertyFilter(DBusProperty):
    """Adds some methods to support the MediaContainer property filtering."""

    def get_properties_for_filter(self, interface, filter_):
        props = self.get_properties(interface)
        if "*" not in filter_:
            props = [p for p in props if p[1] in filter_]
        return props

    def get_values(self, properties, path="/"):
        result = {}
        for iface, prop in properties:
            result[prop] = self.get_value(iface, prop, path)
        return result


class MediaContainer(object):
    IFACE = "org.gnome.UPnP.MediaContainer2"
    ISPEC = """
<property type="u" name="ChildCount" access="read"/>
<property type="u" name="ItemCount" access="read"/>
<property type="u" name="ContainerCount" access="read"/>
<property type="b" name="Searchable" access="read"/>
<property type="o" name="Icon" access="read"/>

<method name="ListChildren">
    <arg type="u" name="offset" direction="in"/>
    <arg type="u" name="max" direction="in"/>
    <arg type="as" name="filter" direction="in"/>
    <arg type="aa{sv}" name="arg_3" direction="out"/>
</method>
<method name="ListContainers">
    <arg type="u" name="offset" direction="in"/>
    <arg type="u" name="max" direction="in"/>
    <arg type="as" name="filter" direction="in"/>
    <arg type="aa{sv}" name="arg_3" direction="out"/>
</method>
<method name="ListItems">
    <arg type="u" name="offset" direction="in"/>
    <arg type="u" name="max" direction="in"/>
    <arg type="as" name="filter" direction="in"/>
    <arg type="aa{sv}" name="arg_3" direction="out"/>
</method>
<method name="SearchObjects">
    <arg type="s" name="query" direction="in"/>
    <arg type="u" name="offset" direction="in"/>
    <arg type="u" name="max" direction="in"/>
    <arg type="as" name="filter" direction="in"/>
    <arg type="aa{sv}" name="arg_4" direction="out"/>
</method>

<signal name="Updated"/>
"""

    def __init__(self, icon=False):
        self.set_introspection(MediaContainer.IFACE, MediaContainer.ISPEC)

        props = ["ChildCount", "ItemCount", "ContainerCount", "Searchable"]
        if icon:
            props.append("Icon")

        for p in props:
            self.register_property(MediaContainer.IFACE, p)

        self.implement_interface(MediaContainer.IFACE, MediaObject.IFACE)

    def emit_updated(self, path="/"):
        self.Updated(rel=path)

    @dbus.service.method(IFACE, in_signature="uuas", out_signature="aa{sv}",
                         rel_path_keyword="path")
    def ListChildren(self, offset, max_, filter_, path):
        if self.SUPPORTS_MULTIPLE_OBJECT_PATHS:
            return self.list_children(offset, max_, filter_, path)
        return self.list_children(offset, max_, filter_)

    @dbus.service.method(IFACE, in_signature="uuas", out_signature="aa{sv}",
                         rel_path_keyword="path")
    def ListContainers(self, offset, max_, filter_, path):
        if self.SUPPORTS_MULTIPLE_OBJECT_PATHS:
            return self.list_containers(offset, max_, filter_, path)
        return self.list_containers(offset, max_, filter_)

    @dbus.service.method(IFACE, in_signature="uuas", out_signature="aa{sv}",
                         rel_path_keyword="path")
    def ListItems(self, offset, max_, filter_, path):
        if self.SUPPORTS_MULTIPLE_OBJECT_PATHS:
            return self.list_items(offset, max_, filter_, path)
        return self.list_items(offset, max_, filter_)

    @dbus.service.method(IFACE, in_signature="suuas", out_signature="aa{sv}",
                         rel_path_keyword="path")
    def SearchObjects(self, query, offset, max_, filter_, path):
        return []

    @dbus.service.signal(IFACE, rel_path_keyword="rel")
    def Updated(self, rel=""):
        pass


class MediaObject(object):
    IFACE = "org.gnome.UPnP.MediaObject2"
    ISPEC = """
<property type="o" name="Parent" access="read"/>
<property type="s" name="Type" access="read"/>
<property type="o" name="Path" access="read"/>
<property type="s" name="DisplayName" access="read"/>
"""
    parent = None

    def __init__(self, parent=None):
        self.set_introspection(MediaObject.IFACE, MediaObject.ISPEC)
        for p in ["Parent", "Type", "Path", "DisplayName"]:
            self.register_property(MediaObject.IFACE, p)
        self.parent = parent or self


class MediaItem(object):
    IFACE = "org.gnome.UPnP.MediaItem2"
    ISPEC = """
<property type="as" name="URLs" access="read"/>
<property type="s" name="MIMEType" access="read"/>
"""

    def __init__(self):
        self.set_introspection(MediaItem.IFACE, MediaItem.ISPEC)
        for p in ["URLs", "MIMEType"]:
            self.register_property(MediaItem.IFACE, p)
        self.implement_interface(MediaItem.IFACE, MediaObject.IFACE)


class EntryObject(MediaContainer, MediaObject, DBusPropertyFilter,
                  DBusIntrospectable, dbus.service.Object):
    BUS_NAME = "org.gnome.UPnP.MediaServer2.QuodLibet"
    PATH = "/org/gnome/UPnP/MediaServer2/QuodLibet"
    DISPLAY_NAME = "@REALNAME@'s Quod Libet on @HOSTNAME@"

    def __init__(self):
        self.__sub = []

        DBusIntrospectable.__init__(self)
        DBusPropertyFilter.__init__(self)
        MediaObject.__init__(self)
        MediaContainer.__init__(self, False)

        bus = dbus.SessionBus()
        name = dbus.service.BusName(self.BUS_NAME, bus)
        dbus.service.Object.__init__(self, bus, self.PATH, name)

    def get_property(self, interface, name):
        if interface == MediaContainer.IFACE:
            if name == "ChildCount":
                return dbus.UInt32(len(self.__sub))
            elif name == "ItemCount":
                return dbus.UInt32(0)
            elif name == "ContainerCount":
                return dbus.UInt32(len(self.__sub))
            elif name == "Searchable":
                return False
        elif interface == MediaObject.IFACE:
            if name == "Parent":
                return dbus.ObjectPath(self.parent.PATH)
            elif name == "Type":
                return "container"
            elif name == "Path":
                return dbus.ObjectPath(self.PATH)
            elif name == "DisplayName":
                return self.DISPLAY_NAME

    def register_child(self, child):
        self.__sub.append(child)
        self.emit_properties_changed(MediaContainer.IFACE,
                                     ["ChildCount", "ContainerCount"])

    def list_containers(self, offset, max_, filter_):
        props = self.get_properties_for_filter(MediaContainer.IFACE, filter_)
        end = (max_ and offset + max_) or None

        result = []
        for sub in self.__sub[offset:end]:
            result.append(sub.get_values(props))
        return result

    list_children = list_containers

    def list_items(self, offset, max_, filter_):
        return []


class DummySongObject(MediaItem, MediaObject, DBusPropertyFilter,
                      DBusIntrospectable):
    """ A dummy song object that is not exported on the bus, but supports
    the usual interfaces.

    You need to assign a real song before using it, and have to pass
    a path prefix.

    The path of the song is /org/gnome/UPnP/MediaServer2/Song/<PREFIX>/SongID
    This lets us reconstruct the original parent path:
    /org/gnome/UPnP/MediaServer2/<PREFIX>

    atm. a prefix can look like "Albums/123456"
    """

    BASE_PATH = "/org/gnome/UPnP/MediaServer2"
    SUPPORTS_MULTIPLE_OBJECT_PATHS = False
    __pattern = Pattern(
        "<discnumber|<discnumber>.><tracknumber>. <title>")

    def __init__(self, parent):
        DBusIntrospectable.__init__(self)
        DBusPropertyFilter.__init__(self)
        MediaObject.__init__(self, parent)
        MediaItem.__init__(self)

    def set_song(self, song, prefix):
        self.__song = song
        self.__prefix = prefix

    def get_property(self, interface, name):
        if interface == MediaObject.IFACE:
            if name == "Parent":
                return dbus.ObjectPath(self.BASE_PATH + "/" + self.__prefix)
            elif name == "Type":
                return "audio"
            elif name == "Path":
                path = SongObject.PATH
                path += "/" + self.__prefix + "/" + str(id(self.__song))
                return path
            elif name == "DisplayName":
                return self.__pattern % self.__song
        elif interface == MediaItem.IFACE:
            if name == "URLs":
                return [self.__song("~uri")]
            elif name == "MIMEType":
                # FIXME
                return "audio/mpeg"


class DummyAlbumObject(MediaContainer, MediaObject, DBusPropertyFilter,
                       DBusIntrospectable):

    SUPPORTS_MULTIPLE_OBJECT_PATHS = False
    __pattern = Pattern("<albumartist|<~albumartist~album>|<~artist~album>>")

    def __init__(self, parent):
        DBusIntrospectable.__init__(self)
        DBusPropertyFilter.__init__(self)
        MediaObject.__init__(self, parent)
        MediaContainer.__init__(self, False)
        self.__song = DummySongObject(self)

    def get_dummy(self, song):
        self.__song.set_song(song, "Albums/" + str(id(self.__album)))
        return self.__song

    def set_album(self, album):
        self.__album = album
        self.PATH = self.parent.PATH + "/" + str(id(album))

    def get_property(self, interface, name):
        if interface == MediaContainer.IFACE:
            if name == "ChildCount" or name == "ItemCount":
                return dbus.UInt32(len(self.__album.songs))
            elif name == "ContainerCount":
                return dbus.UInt32(0)
            elif name == "Searchable":
                return False
        elif interface == MediaObject.IFACE:
            if name == "Parent":
                return dbus.ObjectPath(self.parent.PATH)
            elif name == "Type":
                return "container"
            elif name == "Path":
                return dbus.ObjectPath(self.PATH)
            elif name == "DisplayName":
                return self.__pattern % self.__album

    def list_containers(self, offset, max_, filter_):
        return []

    def list_items(self, offset, max_, filter_):
        songs = sorted(self.__album.songs, key=lambda s: s.sort_key)
        dummy = self.get_dummy(None)
        props = dummy.get_properties_for_filter(MediaItem.IFACE, filter_)
        end = (max_ and offset + max_) or None

        result = []
        for song in songs[offset:end]:
            result.append(self.get_dummy(song).get_values(props))
        return result

    list_children = list_items


class SongObject(MediaItem, MediaObject, DBusProperty, DBusIntrospectable,
                 dbus.service.FallbackObject):
    BUS_NAME = "org.gnome.UPnP.MediaServer2.QuodLibet"
    PATH = "/org/gnome/UPnP/MediaServer2/Song"

    def __init__(self, library, users):
        DBusIntrospectable.__init__(self)
        DBusProperty.__init__(self)
        MediaObject.__init__(self, None)
        MediaItem.__init__(self)

        bus = dbus.SessionBus()
        self.ref = dbus.service.BusName(self.BUS_NAME, bus)
        dbus.service.FallbackObject.__init__(self, bus, self.PATH)

        self.__library = library
        self.__map = dict((id(v), v) for v in self.__library.itervalues())
        self.__reverse = dict((v, k) for k, v in self.__map.iteritems())

        self.__song = DummySongObject(self)

        self.__users = users

        signals = [
            ("changed", self.__songs_changed),
            ("removed", self.__songs_removed),
            ("added", self.__songs_added),
        ]
        self.__sigs = map(lambda (s, f): self.__library.connect(s, f), signals)

    def __songs_changed(self, lib, songs):
        # We don't know what changed, so get all properties
        props = [p[1] for p in self.get_properties(MediaItem.IFACE)]

        for song in songs:
            song_id = str(id(song))
            for user in self.__users:
                # ask the user for the prefix whith which the song is used
                prefix = user.get_prefix(song)
                path = "/" + prefix + "/" + song_id
                self.emit_properties_changed(MediaItem.IFACE, props, path)

    def __songs_added(self, lib, songs):
        for song in songs:
            new_id = id(song)
            self.__map[new_id] = song
            self.__reverse[song] = new_id

    def __songs_removed(self, lib, songs):
        for song in songs:
            del self.__map[self.__reverse[song]]
            del self.__reverse[song]

    def remove_from_connection(self):
        super(SongObject, self).remove_from_connection()
        map(self.__library.disconnect, self.__sigs)

    def get_dummy(self, song, prefix):
        self.__song.set_song(song, prefix)
        return self.__song

    def get_property(self, interface, name, path):
        # extract the prefix
        prefix, song_id = path[1:].rsplit("/", 1)
        song = self.__map[int(song_id)]
        return self.get_dummy(song, prefix).get_property(interface, name)


class AlbumsObject(MediaContainer, MediaObject, DBusPropertyFilter,
                   DBusIntrospectable, dbus.service.FallbackObject):
    BUS_NAME = "org.gnome.UPnP.MediaServer2.QuodLibet"
    PATH = "/org/gnome/UPnP/MediaServer2/Albums"
    DISPLAY_NAME = "Albums"

    __library = None

    def __init__(self, parent, library):
        DBusIntrospectable.__init__(self)
        DBusPropertyFilter.__init__(self)
        MediaObject.__init__(self, parent)
        MediaContainer.__init__(self, False)

        bus = dbus.SessionBus()
        self.ref = dbus.service.BusName(self.BUS_NAME, bus)
        dbus.service.FallbackObject.__init__(self, bus, self.PATH)

        parent.register_child(self)

        self.__library = library.albums
        self.__library.load()

        self.__map = dict((id(v), v) for v in self.__library.itervalues())
        self.__reverse = dict((v, k) for k, v in self.__map.iteritems())

        signals = [
            ("changed", self.__albums_changed),
            ("removed", self.__albums_removed),
            ("added", self.__albums_added),
        ]
        self.__sigs = map(lambda (s, f): self.__library.connect(s, f), signals)

        self.__dummy = DummyAlbumObject(self)

    def get_dummy(self, album):
        self.__dummy.set_album(album)
        return self.__dummy

    def get_path_dummy(self, path):
        return self.get_dummy(self.__map[int(path[1:])])

    def __albums_changed(self, lib, albums):
        for album in albums:
            rel_path = "/" + str(id(album))
            self.emit_updated(rel_path)
            self.emit_properties_changed(
                MediaContainer.IFACE,
                ["ChildCount", "ItemCount", "DisplayName"],
                rel_path)

    def __albums_added(self, lib, albums):
        for album in albums:
            new_id = id(album)
            self.__map[new_id] = album
            self.__reverse[album] = new_id
        self.emit_updated()
        self.emit_properties_changed(MediaContainer.IFACE,
                                     ["ChildCount", "ContainerCount"])

    def __albums_removed(self, lib, albums):
        for album in albums:
            del self.__map[self.__reverse[album]]
            del self.__reverse[album]
        self.emit_updated()
        self.emit_properties_changed(MediaContainer.IFACE,
                                     ["ChildCount", "ContainerCount"])

    def get_prefix(self, song):
        album = self.__library[song.album_key]
        return "Albums/" + str(id(album))

    def remove_from_connection(self):
        super(AlbumsObject, self).remove_from_connection()
        map(self.__library.disconnect, self.__sigs)

    def __get_albums_property(self, interface, name):
        if interface == MediaContainer.IFACE:
            if name == "ChildCount":
                return dbus.UInt32(len(self.__library))
            elif name == "ItemCount":
                return dbus.UInt32(0)
            elif name == "ContainerCount":
                return dbus.UInt32(len(self.__library))
            elif name == "Searchable":
                return False
        elif interface == MediaObject.IFACE:
            if name == "Parent":
                return dbus.ObjectPath(self.parent.PATH)
            elif name == "Type":
                return "container"
            elif name == "Path":
                return dbus.ObjectPath(self.PATH)
            elif name == "DisplayName":
                return self.DISPLAY_NAME

    def get_property(self, interface, name, path):
        if path == "/":
            return self.__get_albums_property(interface, name)

        return self.get_path_dummy(path).get_property(interface, name)

    def __list_albums(self, offset, max_, filter_):
        props = self.get_properties_for_filter(MediaContainer.IFACE, filter_)
        albums = sorted(self.__library, key=lambda a: a.sort)
        end = (max_ and offset + max_) or None

        result = []
        for album in albums[offset:end]:
            result.append(self.get_dummy(album).get_values(props))
        return result

    def list_containers(self, offset, max_, filter_, path):
        if path == "/":
            return self.__list_albums(offset, max_, filter_)
        return []

    def list_items(self, offset, max_, filter_, path):
        if path != "/":
            return self.get_path_dummy(path).list_items(offset, max_, filter_)
        return []

    def list_children(self, offset, max_, filter_, path):
        if path == "/":
            return self.__list_albums(offset, max_, filter_)
        return self.get_path_dummy(path).list_children(offset, max_, filter_)
