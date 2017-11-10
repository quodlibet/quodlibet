# -*- coding: utf-8 -*-
# Copyright 2014 Christoph Reiter <reiter.christoph@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from contextlib import contextmanager

try:
    import dbus
except ImportError:
    dbus = None

from quodlibet.util import print_d


def alternative_service_name(name):
    if "#" in name:
        name, num = name.rsplit("#", 1)
        num = int(num)
    else:
        num = 1
    return "%s#%d" % (name, num + 1)


class AvahiPublishFlags(object):
    NONE = 0
    UNIQUE = 1 << 0
    NO_PROBE = 1 << 1
    NO_ANNOUNCE = 1 << 2
    ALLOW_MULTIPLE = 1 << 3
    NO_REVERSE = 1 << 4
    NO_COOKIE = 1 << 5
    UPDATE = 1 << 6
    USE_WIDE_AREA = 1 << 7
    USE_MULTICAST = 1 << 8


class AvahiEntryGroupState(object):
    UNCOMMITED = 0
    REGISTERING = 1
    ESTABLISHED = 2
    COLLISION = 3
    FAILURE = 4


class AvahiServerState(object):
    INVALID = 0
    REGISTERING = 1
    RUNNING = 2
    COLLISION = 3
    FAILURE = 4


class AvahiProtocol(object):
    INET = 0
    INET6 = 1
    UNSPEC = -1


AVAHI_IF_UNSPEC = -1


class AvahiError(Exception):
    pass


@contextmanager
def ignored(*exceptions):
    try:
        yield
    except exceptions:
        pass


class AvahiService(object):
    """Register a single network service using zeroconf/avahi

    service = AvahiService()
    service.register("foo", 4242, "_mpd._tcp")
    service.register("foo", 2424, "_mpd._tcp")
    service.unregister()

    http://avahi.org/download/doxygen/
    """

    DBUS_NAME = "org.freedesktop.Avahi"
    DBUS_PATH_SERVER = "/"
    DBUS_INTERFACE_ENTRY_GROUP = "org.freedesktop.Avahi.EntryGroup"
    DBUS_INTERFACE_SERVER = "org.freedesktop.Avahi.Server"

    def register(self, name, port, stype):
        """Register the service with avahi.

        Can be called multiple times and will update the service entry
        each time. In case Avahi isn't running or ready, the service
        will be registered when it is ready.

        Can raise AvahiError
        """

        if not dbus:
            raise AvahiError("no dbus bindings")

        try:
            dbus.UInt16(port)
        except OverflowError as e:
            raise AvahiError(e)

        self.name = name
        self._real_name = name
        self.port = port
        self.stype = stype

        try:
            bus = dbus.SystemBus()
            if not self._watch:
                self._watch = bus.watch_name_owner(
                    self.DBUS_NAME, self._owner_changed)
            else:
                self._try_update_service()
        except dbus.DBusException as e:
            raise AvahiError(e)

    def unregister(self):
        """Unregister the service.

        Can be called multiple times. In case you want to update,
        call register() with new data instead.

        Will not raise.
        """

        if self._watch:
            with ignored(dbus.DBusException):
                self._watch.cancel()
            self._watch = None

        self._remove_server()

    def __init__(self):
        self.name = None
        self.stype = None
        self.port = None

        self._group = None
        self._group_id = None
        self._server_id = None
        self._watch = None
        self._real_name = None
        self._last_server_state = None

    def _group_state_change(self, state, *args):
        if state == AvahiEntryGroupState.COLLISION:
            self._real_name = alternative_service_name(self._real_name)
            self._try_update_service()

    def _add_service(self):
        assert not self._group
        assert not self._group_id

        try:
            bus = dbus.SystemBus()
            server_obj = bus.get_object(self.DBUS_NAME, self.DBUS_PATH_SERVER)
            server = dbus.Interface(server_obj, self.DBUS_INTERFACE_SERVER)

            group_path = server.EntryGroupNew()
            group_obj = bus.get_object(self.DBUS_NAME, group_path)
            group = dbus.Interface(group_obj, self.DBUS_INTERFACE_ENTRY_GROUP)

            self._group_id = group.connect_to_signal(
                "StateChanged", self._group_state_change)
            flags = AvahiPublishFlags.NONE

            print_d("name=%s, flags=%x, stype=%s, port=%d" % (
                self._real_name, flags, self.stype, self.port))
            group.AddService(
                AVAHI_IF_UNSPEC, AvahiProtocol.UNSPEC,
                dbus.UInt32(flags), self._real_name, self.stype,
                dbus.String(), dbus.String(), dbus.UInt16(self.port), [])
            group.Commit()
            self._group = group
        except dbus.DBusException:
            self._remove_service()

    def _try_update_service(self):
        if not self._group:
            return
        assert self._group_id

        try:
            group = self._group
            # XXX: http://markmail.org/message/b5d5wa2tdcplxpk2
            # It's "documented" that Reset() shouldn't be called in this case
            # but it doesn't work otherwise...
            group.Reset()
            flags = AvahiPublishFlags.UPDATE

            print_d("name=%s, flags=%x, stype=%s, port=%d" % (
                self._real_name, flags, self.stype, self.port))
            group.AddService(
                AVAHI_IF_UNSPEC, AvahiProtocol.UNSPEC,
                dbus.UInt32(flags), self._real_name, self.stype,
                dbus.String(), dbus.String(), dbus.UInt16(self.port), [])
            group.Commit()
        except dbus.DBusException:
            self._remove_service()

    def _remove_service(self):
        if self._group_id:
            with ignored(dbus.DBusException):
                self._group_id.remove()
            self._group_id = None

        if self._group:
            with ignored(dbus.DBusException):
                self._group.Free()
            self._group = None

    def _remove_server(self):
        if self._server_id:
            with ignored(dbus.DBusException):
                self._server_id.remove()
            self._server_id = None

        self._last_server_state = None

        self._remove_service()

    def _add_server(self):
        assert not self._server_id

        try:
            bus = dbus.SystemBus()
            server_obj = bus.get_object(self.DBUS_NAME, self.DBUS_PATH_SERVER)
            server = dbus.Interface(server_obj, self.DBUS_INTERFACE_SERVER)
            self._server_id = server.connect_to_signal(
                "StateChanged", self._server_state_changed)
            self._server_state_changed(server.GetState())
        except dbus.DBusException:
            self._remove_server()

    def _server_state_changed(self, state, *args):
        # protect from calling this twice in a row for the same state
        # because we have to call this manually on start and can't
        # be sure if the signal fires as well
        if state == self._last_server_state:
            return
        self._last_server_state = state

        if state == AvahiServerState.RUNNING:
            self._add_service()
        elif state in (AvahiServerState.COLLISION,
                       AvahiServerState.REGISTERING):
            self._remove_service()

    def _owner_changed(self, owner):
        if owner:
            self._add_server()
        else:
            self._remove_server()
