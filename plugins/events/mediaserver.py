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
        song = SongObject(library)

        self.objects = [entry, albums, song]

    def disabled(self):
        for obj in self.objects:
            obj.remove_from_connection()
        self.objects = []


class DBusIntrospectable(object):
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

    def register_property(self, interface, name):
        self.__props.setdefault(interface, []).append(name)
        self.__impl.setdefault(interface, [])

    def implement_interface(self, iface, sub_iface):
        self.__props.setdefault(iface, [])
        self.__props.setdefault(sub_iface, [])
        self.__impl.setdefault(iface, []).append(sub_iface)

    def get_properties(self, interface):
        result = list(self.__props[interface])
        for sub in self.__impl[interface]:
            result.extend(self.get_properties(sub))
        return result

    def get_properties_for_filter(self, interface, filter_, path="/"):
        props = self.get_properties(interface)
        if "*" not in filter_:
            props = [p for p in props if p in filter_]

        values = {}
        for prop in props:
            sub = self.get_interface(interface, prop)
            if self.SUPPORTS_MULTIPLE_OBJECT_PATHS:
                values[prop] = self.get_property(sub, prop, path)
            else:
                values[prop] = self.get_property(sub, prop)
        return values

    def get_interface(self, interface, prop):
        if prop in self.__props[interface]:
            return interface
        for sub in self.__impl[interface]:
            if self.get_interface(sub, prop):
                return sub

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
        for prop in self.get_properties(interface):
            sub = self.get_interface(interface, prop)
            if self.SUPPORTS_MULTIPLE_OBJECT_PATHS:
                values[prop] = self.get_property(sub, prop, path)
            else:
                values[prop] = self.get_property(sub, prop)
        return values

    @dbus.service.signal(IFACE, signature="sa{sv}as", rel_path_keyword="path")
    def PropertiesChanged(self, interface, changed, invalidated, path="/"):
        pass


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
        return self.list_items(offset, max_, filter_, path)

    @dbus.service.method(IFACE, in_signature="suuas", out_signature="aa{sv}",
                         rel_path_keyword="path")
    def SearchObjects(self, query, offset, max_, filter_, path):
        return []

    @dbus.service.signal(IFACE, rel_path_keyword="path")
    def Updated(self, path="/"):
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


class EntryObject(MediaContainer, MediaObject, DBusProperty,
                  DBusIntrospectable, dbus.service.Object):
    BUS_NAME = "org.gnome.UPnP.MediaServer2.QuodLibet"
    PATH = "/org/gnome/UPnP/MediaServer2/QuodLibet"
    DISPLAY_NAME = "@REALNAME@'s Quod Libet on @HOSTNAME@"

    def __init__(self):
        self.__sub = []

        DBusIntrospectable.__init__(self)
        DBusProperty.__init__(self)
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

    def list_containers(self, offset, max_, filter_):
        result = []
        end = (max_ and offset + max_) or None
        for sub in self.__sub[offset:end]:
            d = sub.get_properties_for_filter(MediaContainer.IFACE, filter_)
            result.append(d)
        return result

    list_children = list_containers

    def list_items(self, offset, max_, filter_):
        return []


class DummySongObject(MediaItem, MediaObject, DBusProperty,
                        DBusIntrospectable):

    SUPPORTS_MULTIPLE_OBJECT_PATHS = False
    __pattern = Pattern(
        "<discnumber|<discnumber>.><tracknumber>. <title>")

    def __init__(self, parent):
        DBusIntrospectable.__init__(self)
        DBusProperty.__init__(self)
        MediaObject.__init__(self, parent)
        MediaItem.__init__(self)

    def set_song(self, song):
        self.__song = song
        self.PATH = SongObject.PATH + "/" + str(id(song))

    def get_property(self, interface, name):
        if interface == MediaObject.IFACE:
            if name == "Parent":
                return dbus.ObjectPath(self.parent.PATH)
            elif name == "Type":
                return "audio"
            elif name == "Path":
                return dbus.ObjectPath(self.PATH)
            elif name == "DisplayName":
                return self.__pattern % self.__song
        elif interface == MediaItem.IFACE:
            if name == "URLs":
                return [self.__song("~uri")]
            elif name == "MIMEType":
                # FIXME
                return "audio/mpeg"


class DummyAlbumObject(MediaContainer, MediaObject, DBusProperty,
                        DBusIntrospectable):

    SUPPORTS_MULTIPLE_OBJECT_PATHS = False
    __pattern = Pattern("<albumartist|<~albumartist~album>|<~artist~album>>")

    def __init__(self, parent):
        DBusIntrospectable.__init__(self)
        DBusProperty.__init__(self)
        MediaObject.__init__(self, parent)
        MediaContainer.__init__(self, False)

        self.__song = DummySongObject(self)

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
        end = (max_ and offset + max_) or None

        result = []
        for song in songs[offset:end]:
            self.__song.set_song(song)
            d = self.__song.get_properties_for_filter(MediaItem.IFACE, filter_)
            result.append(d)
        return result

    list_children = list_items


class SongObject(MediaItem, MediaObject, DBusProperty, DBusIntrospectable,
                 dbus.service.FallbackObject):
    BUS_NAME = "org.gnome.UPnP.MediaServer2.QuodLibet"
    PATH = "/org/gnome/UPnP/MediaServer2/Song"

    def __init__(self, library):
        DBusIntrospectable.__init__(self)
        DBusProperty.__init__(self)
        MediaObject.__init__(self, None)
        MediaItem.__init__(self)

        bus = dbus.SessionBus()
        self.ref = dbus.service.BusName(self.BUS_NAME, bus)
        dbus.service.FallbackObject.__init__(self, bus, self.PATH)

        self.__library = library
        self.__map = {}
        for song in self.__library:
            self.__map[id(song)] = song

        self.__song = DummySongObject(self)

    def get_property(self, interface, name, path):
        song_id = int(path[1:])
        song = self.__map[song_id]
        self.__song.set_song(song)
        return self.__song.get_property(interface, name)


class AlbumsObject(MediaContainer, MediaObject, DBusProperty,
                   DBusIntrospectable, dbus.service.FallbackObject):
    BUS_NAME = "org.gnome.UPnP.MediaServer2.QuodLibet"
    PATH = "/org/gnome/UPnP/MediaServer2/Albums"
    DISPLAY_NAME = "Albums"

    __library = None

    def __init__(self, parent, library):
        DBusIntrospectable.__init__(self)
        DBusProperty.__init__(self)
        MediaObject.__init__(self, parent)
        MediaContainer.__init__(self, False)

        bus = dbus.SessionBus()
        self.ref = dbus.service.BusName(self.BUS_NAME, bus)
        dbus.service.FallbackObject.__init__(self, bus, self.PATH)

        parent.register_child(self)

        self.__library = library.albums
        self.__library.load()

        self.__map = {}
        for album in self.__library:
            self.__map[id(album)] = album

        self.__album = DummyAlbumObject(self)

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

    def __get_album_for_path(self, path):
        return self.__map[int(path)]

    def get_property(self, interface, name, path):
        if path == "/":
            return self.__get_albums_property(interface, name)

        album = self.__get_album_for_path(path[1:])
        self.__album.set_album(album)
        return self.__album.get_property(interface, name)

    def __list_albums(self, offset, max_, filter_):
        albums = sorted(self.__library, key=lambda a: a.sort)
        end = (max_ and offset + max_) or None

        result = []
        for album in albums[offset:end]:
            self.__album.set_album(album)
            d = self.__album.get_properties_for_filter(MediaContainer.IFACE,
                                                       filter_)
            result.append(d)
        return result

    def list_containers(self, offset, max_, filter_, path):
        if path == "/":
            return self.__list_albums(offset, max_, filter_)
        return []

    def list_items(self, offset, max_, filter_, path):
        if path != "/":
            album = self.__get_album_for_path(path[1:])
            self.__album.set_album(album)
            return self.__album.list_items(offset, max_, filter_)
        return []

    def list_children(self, offset, max_, filter_, path):
        if path == "/":
            return self.__list_albums(offset, max_, filter_)
        album = self.__get_album_for_path(path[1:])
        self.__album.set_album(album)
        return self.__album.list_children(offset, max_, filter_)
