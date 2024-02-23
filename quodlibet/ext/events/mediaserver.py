# Copyright 2012,2013 Christoph Reiter <reiter.christoph@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import sys

if os.name == "nt" or sys.platform == "darwin":
    from quodlibet.plugins import PluginNotSupportedError
    raise PluginNotSupportedError

from gi.repository import Gtk, GdkPixbuf
from senf import fsn2uri

import dbus
import dbus.service

from quodlibet import _
from quodlibet import app
from quodlibet.plugins.events import EventPlugin
from quodlibet.pattern import Pattern
from quodlibet.qltk import Icons
from quodlibet.util.dbusutils import DBusIntrospectable, DBusProperty
from quodlibet.util.dbusutils import dbus_unicode_validate as unival
from quodlibet.util import NamedTemporaryFile

BASE_PATH = "/org/gnome/UPnP/MediaServer2"
BUS_NAME = "org.gnome.UPnP.MediaServer2.QuodLibet"


class MediaServer(EventPlugin):
    PLUGIN_ID = "mediaserver"
    PLUGIN_NAME = _("UPnP AV Media Server")
    PLUGIN_DESC = _("Exposes all albums to the Rygel UPnP Media Server "
                    "through the MediaServer2 D-Bus interface.")
    PLUGIN_ICON = Icons.NETWORK_WORKGROUP

    def PluginPreferences(self, parent):
        vbox = Gtk.VBox(spacing=12)

        conf_exp = _("Ensure the following is in your rygel config file "
                      "(~/.config/rygel.conf):")
        conf_cont = ("[External]\n"
                     "enabled=true\n\n"
                     "[org.gnome.UPnP.MediaServer2.QuodLibet]\n"
                     "enabled=true")

        exp_lbl = Gtk.Label(label=conf_exp)
        exp_lbl.set_selectable(True)
        exp_lbl.set_line_wrap(True)
        exp_lbl.set_alignment(0, 0)

        conf_lbl = Gtk.Label()
        conf_lbl.set_selectable(True)
        conf_lbl.set_alignment(0, 0)
        conf_lbl.set_markup(f"<span font='mono'>{conf_cont}</span>")

        vbox.pack_start(exp_lbl, True, False, 0)
        vbox.pack_start(conf_lbl, True, False, 0)
        return vbox

    def enabled(self):
        try:
            dbus.SessionBus()
        except dbus.DBusException:
            self.objects = []
            return

        entry = EntryObject()
        albums = AlbumsObject(entry, app.library)
        song = SongObject(app.library, [albums])
        icon = Icon(entry)

        self.objects = [entry, albums, song, icon]

    def disabled(self):
        for obj in self.objects:
            obj.remove_from_connection()

        for obj in self.objects:
            obj.destroy()

        del self.objects

        import gc
        gc.collect()


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


class MediaContainer:
    IFACE = "org.gnome.UPnP.MediaContainer2"
    ISPEC_PROP = """
<property type="u" name="ChildCount" access="read"/>
<property type="u" name="ItemCount" access="read"/>
<property type="u" name="ContainerCount" access="read"/>
<property type="b" name="Searchable" access="read"/>
<property type="o" name="Icon" access="read"/>
"""
    ISPEC = """
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

    def __init__(self, optional=()):
        self.set_introspection(MediaContainer.IFACE, MediaContainer.ISPEC)

        props = ["ChildCount", "ItemCount", "ContainerCount", "Searchable"]
        props += list(optional)
        self.set_properties(MediaContainer.IFACE, MediaContainer.ISPEC_PROP,
                            wl=props)

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


class MediaObject:
    IFACE = "org.gnome.UPnP.MediaObject2"
    ISPEC = """
<property type="o" name="Parent" access="read"/>
<property type="s" name="Type" access="read"/>
<property type="o" name="Path" access="read"/>
<property type="s" name="DisplayName" access="read"/>
"""
    parent = None

    def __init__(self, parent=None):
        self.set_properties(MediaObject.IFACE, MediaObject.ISPEC)
        self.parent = parent or self


class MediaItem:
    IFACE = "org.gnome.UPnP.MediaItem2"
    ISPEC = """
<property type="as" name="URLs" access="read"/>
<property type="s" name="MIMEType" access="read"/>

<property type="x" name="Size" access="read"/>
<property type="s" name="Artist" access="read"/>
<property type="s" name="Album" access="read"/>
<property type="s" name="Date" access="read"/>
<property type="s" name="Genre" access="read"/>
<property type="s" name="DLNAProfile" access="read"/>

<property type="i" name="Duration" access="read"/>
<property type="i" name="Bitrate" access="read"/>
<property type="i" name="SampleRate" access="read"/>
<property type="i" name="BitsPerSample" access="read"/>

<property type="i" name="Width" access="read"/>
<property type="i" name="Height" access="read"/>
<property type="i" name="ColorDepth" access="read"/>
<property type="i" name="PixelWidth" access="read"/>
<property type="i" name="PixelHeight" access="read"/>
<property type="o" name="Thumbnail" access="read"/>

<property type="o" name="AlbumArt" access="read"/>

<property type="i" name="TrackNumber" access="read"/>
"""

    def __init__(self, optional=()):
        props = ["URLs", "MIMEType"] + list(optional)
        self.set_properties(MediaItem.IFACE, MediaItem.ISPEC, wl=props)
        self.implement_interface(MediaItem.IFACE, MediaObject.IFACE)


class EntryObject(MediaContainer, MediaObject, DBusPropertyFilter,
                  DBusIntrospectable, dbus.service.Object):
    PATH = BASE_PATH + "/QuodLibet"
    DISPLAY_NAME = "@REALNAME@'s Quod Libet on @HOSTNAME@"

    def __init__(self):
        self.__sub = []

        DBusIntrospectable.__init__(self)
        DBusPropertyFilter.__init__(self)
        MediaObject.__init__(self)
        MediaContainer.__init__(self, optional=["Icon"])

        bus = dbus.SessionBus()
        name = dbus.service.BusName(BUS_NAME, bus)
        dbus.service.Object.__init__(self, bus, self.PATH, name)

    def get_property(self, interface, name):
        if interface == MediaContainer.IFACE:
            if name == "ChildCount":
                return len(self.__sub)
            elif name == "ItemCount":
                return 0
            elif name == "ContainerCount":
                return len(self.__sub)
            elif name == "Searchable":
                return False
            elif name == "Icon":
                return Icon.PATH
        elif interface == MediaObject.IFACE:
            if name == "Parent":
                return self.parent.PATH
            elif name == "Type":
                return "container"
            elif name == "Path":
                return self.PATH
            elif name == "DisplayName":
                return self.DISPLAY_NAME

    def destroy(self):
        # break cycle
        del self.__sub
        del self.parent

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

SUPPORTED_SONG_PROPERTIES = ("Size", "Artist", "Album", "Date", "Genre",
                             "Duration", "TrackNumber")


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

    SUPPORTS_MULTIPLE_OBJECT_PATHS = False
    __pattern = Pattern(
        "<discnumber|<discnumber>.><tracknumber>. <title>")

    def __init__(self, parent):
        DBusIntrospectable.__init__(self)
        DBusPropertyFilter.__init__(self)
        MediaObject.__init__(self, parent)
        MediaItem.__init__(self, optional=SUPPORTED_SONG_PROPERTIES)

    def set_song(self, song, prefix):
        self.__song = song
        self.__prefix = prefix

    def get_property(self, interface, name):
        if interface == MediaObject.IFACE:
            if name == "Parent":
                return BASE_PATH + "/" + self.__prefix
            elif name == "Type":
                return "music"
            elif name == "Path":
                path = SongObject.PATH
                path += "/" + self.__prefix + "/" + str(id(self.__song))
                return path
            elif name == "DisplayName":
                return unival(self.__song.comma("title"))
        elif interface == MediaItem.IFACE:
            if name == "URLs":
                return [self.__song("~uri")]
            elif name == "MIMEType":
                mimes = self.__song.mimes
                return mimes and mimes[0]
            elif name == "Size":
                return self.__song("~#filesize")
            elif name == "Artist":
                return unival(self.__song.comma("artist"))
            elif name == "Album":
                return unival(self.__song.comma("album"))
            elif name == "Date":
                return unival(self.__song.comma("date"))
            elif name == "Genre":
                return unival(self.__song.comma("genre"))
            elif name == "Duration":
                return self.__song("~#length")
            elif name == "TrackNumber":
                return self.__song("~#track", 0)


class DummyAlbumObject(MediaContainer, MediaObject, DBusPropertyFilter,
                       DBusIntrospectable):

    SUPPORTS_MULTIPLE_OBJECT_PATHS = False
    __pattern = Pattern("<albumartist|<~albumartist~album>|<~artist~album>>")

    def __init__(self, parent):
        DBusIntrospectable.__init__(self)
        DBusPropertyFilter.__init__(self)
        MediaObject.__init__(self, parent)
        MediaContainer.__init__(self)
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
                return len(self.__album.songs)
            elif name == "ContainerCount":
                return 0
            elif name == "Searchable":
                return False
        elif interface == MediaObject.IFACE:
            if name == "Parent":
                return self.parent.PATH
            elif name == "Type":
                return "container"
            elif name == "Path":
                return self.PATH
            elif name == "DisplayName":
                return unival(self.__pattern % self.__album)

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
    PATH = BASE_PATH + "/Song"

    def __init__(self, library, users):
        DBusIntrospectable.__init__(self)
        DBusProperty.__init__(self)
        MediaObject.__init__(self, None)
        MediaItem.__init__(self, optional=SUPPORTED_SONG_PROPERTIES)

        bus = dbus.SessionBus()
        self.ref = dbus.service.BusName(BUS_NAME, bus)
        dbus.service.FallbackObject.__init__(self, bus, self.PATH)

        self.__library = library
        self.__map = {id(v): v for v in self.__library.values()}
        self.__reverse = {v: k for k, v in self.__map.items()}

        self.__song = DummySongObject(self)

        self.__users = users

        signals = [
            ("changed", self.__songs_changed),
            ("removed", self.__songs_removed),
            ("added", self.__songs_added),
        ]
        self.__sigs = (self.__library.connect(x[0], x[1]) for x in signals)

    def __songs_changed(self, lib, songs):
        # We don't know what changed, so get all properties
        props = [p[1] for p in self.get_properties(MediaItem.IFACE)]

        for song in songs:
            song_id = str(id(song))
            # https://github.com/quodlibet/quodlibet/issues/id=1127
            # XXX: Something is emitting wrong changed events..
            # ignore song_ids we don't know for now
            if song_id not in self.__map:
                continue
            for user in self.__users:
                # ask the user for the prefix with which the song is used
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

    def destroy(self):
        for signal_id in self.__sigs:
            self.__library.disconnect(signal_id)

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
    PATH = BASE_PATH + "/Albums"
    DISPLAY_NAME = "Albums"

    def __init__(self, parent, library):
        DBusIntrospectable.__init__(self)
        DBusPropertyFilter.__init__(self)
        MediaObject.__init__(self, parent)
        MediaContainer.__init__(self)

        bus = dbus.SessionBus()
        self.ref = dbus.service.BusName(BUS_NAME, bus)
        dbus.service.FallbackObject.__init__(self, bus, self.PATH)

        parent.register_child(self)

        self.__library = library.albums
        self.__library.load()

        self.__map = {id(v): v for v in self.__library.values()}
        self.__reverse = {v: k for k, v in self.__map.items()}

        signals = [
            ("changed", self.__albums_changed),
            ("removed", self.__albums_removed),
            ("added", self.__albums_added),
        ]
        self.__sigs = (self.__library.connect(x[0], x[1]) for x in signals)

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

    def destroy(self):
        for signal_id in self.__sigs:
            self.__library.disconnect(signal_id)

    def __get_albums_property(self, interface, name):
        if interface == MediaContainer.IFACE:
            if name == "ChildCount":
                return len(self.__library)
            elif name == "ItemCount":
                return 0
            elif name == "ContainerCount":
                return len(self.__library)
            elif name == "Searchable":
                return False
        elif interface == MediaObject.IFACE:
            if name == "Parent":
                return self.parent.PATH
            elif name == "Type":
                return "container"
            elif name == "Path":
                return self.PATH
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


class Icon(MediaItem, MediaObject, DBusProperty, DBusIntrospectable,
                 dbus.service.Object):
    PATH = BASE_PATH + "/Icon"

    SIZE = 160

    def __init__(self, parent):
        DBusIntrospectable.__init__(self)
        DBusProperty.__init__(self)
        MediaObject.__init__(self, parent=parent)
        MediaItem.__init__(self, optional=["Height", "Width", "ColorDepth"])

        bus = dbus.SessionBus()
        name = dbus.service.BusName(BUS_NAME, bus)
        dbus.service.Object.__init__(self, bus, self.PATH, name)

        # https://bugzilla.gnome.org/show_bug.cgi?id=669677
        self.implement_interface("org.gnome.UPnP.MediaItem1", MediaItem.IFACE)

        # load into a pixbuf
        theme = Gtk.IconTheme.get_default()
        pixbuf = theme.load_icon(Icons.QUODLIBET, Icon.SIZE, 0)

        # make sure the size is right
        pixbuf = pixbuf.scale_simple(Icon.SIZE, Icon.SIZE,
                                     GdkPixbuf.InterpType.BILINEAR)
        self.__depth = pixbuf.get_bits_per_sample()

        # save and keep reference
        self.__f = f = NamedTemporaryFile()
        pixbuf.savev(f.name, "png", [], [])

    def get_property(self, interface, name):
        if interface == MediaObject.IFACE:
            if name == "Parent":
                return EntryObject.PATH
            elif name == "Type":
                return "image"
            elif name == "Path":
                return Icon.PATH
            elif name == "DisplayName":
                return r"I'm an icon \o/"
        elif interface == MediaItem.IFACE:
            if name == "URLs":
                return [fsn2uri(self.__f.name)]
            elif name == "MIMEType":
                return "image/png"
            elif name == "Width" or name == "Height":
                return Icon.SIZE
            elif name == "ColorDepth":
                return self.__depth

    def destroy(self):
        pass
