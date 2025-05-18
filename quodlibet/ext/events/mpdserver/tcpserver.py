# Copyright 2014 Christoph Reiter <reiter.christoph@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""A reactive tcp server"""

import socket
import errno

from gi.repository import Gio, GLib

from quodlibet.qltk import io_add_watch


class ServerError(Exception):
    pass


class BaseTCPServer:
    def __init__(self, port, connection_class, debug=False):
        """port -- IP port
        connection_class -- BaseTCPConnection subclass
        """

        self._connections = []
        self._port = port
        self._connection_class = connection_class
        self._sock_service = None
        self._debug = debug

    def log(self, msg):
        """Override for logging"""

    def start(self):
        """Start accepting connections.

        May raise ServerError.
        """

        assert not self._sock_service

        service = Gio.SocketService.new()
        try:
            service.add_inet_port(self._port, None)
        except GLib.GError as e:
            raise ServerError(e) from e
        except OverflowError as e:
            raise ServerError(f"port: {e}") from e
        self._id = service.connect("incoming", self._incoming_connection_cb)
        service.start()
        self._sock_service = service

    def stop(self):
        """Stop accepting connections and close all existing connections.

        Can be called multiple times.
        """

        if not self._sock_service:
            return

        self._sock_service.disconnect(self._id)
        if self._sock_service.is_active():
            self._sock_service.stop()
        self._sock_service = None

        for conn in list(self._connections):
            conn.close()

        assert not self._connections, self._connections

    def handle_init(self):
        """Gets called if a new connection starts and there was none before"""

    def handle_idle(self):
        """Gets called once the last connection closes"""

    def _remove_connection(self, conn):
        """Called by the connection class on close"""

        self._connections.remove(conn)
        del conn._gio_connection

        if not self._connections:
            self.handle_idle()

    def _incoming_connection_cb(self, service, connection, *args):
        try:
            addr = connection.get_remote_address()
        except GLib.GError:
            addr_string = "?.?.?.?"
        else:
            addr_string = addr.get_address().to_string()

        fd = connection.get_socket().get_fd()
        sock = socket.fromfd(fd, socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(0)

        msg = "New connection from %s at socket %d" % (addr_string, sock.fileno())
        if self._debug:
            self.log(msg)

        if not self._connections:
            self.handle_init()
        tcp_conn = self._connection_class(self, sock)
        self._connections.append(tcp_conn)
        # XXX: set unneeded `connection` to keep the reference
        tcp_conn._gio_connection = connection
        tcp_conn.handle_init(self)


class BaseTCPConnection:
    """Abstract base class for TCP connections.

    Subclasses need to implement the handle_*() can_*() methods.
    """

    def __init__(self, server, sock):
        self._server = server
        self._sock = sock

        self._in_id = None
        self._out_id = None
        self._closed = False

    @property
    def name(self):
        return str(self._sock.fileno())

    def start_read(self):
        """Start to read and call handle_read() if data is available.

        Only call once.
        """

        assert self._in_id is None and not self._closed

        def can_read_cb(sock, flags, *args):
            if flags & (GLib.IOCondition.HUP | GLib.IOCondition.ERR):
                self.close()
                return False

            if flags & GLib.IOCondition.IN:
                while True:
                    try:
                        data = sock.recv(4096)
                    except OSError as e:
                        if e.errno in (errno.EWOULDBLOCK, errno.EAGAIN):
                            return True
                        if e.errno == errno.EINTR:
                            continue
                        self.close()
                        return False
                    break

                if not data:
                    self.close()
                    return False

                self.handle_read(data)
                # the implementation could close in handle_read()
                if not self._closed:
                    self.start_write()

            return True

        self._in_id = io_add_watch(
            self._sock,
            GLib.PRIORITY_DEFAULT,
            GLib.IOCondition.IN | GLib.IOCondition.ERR | GLib.IOCondition.HUP,
            can_read_cb,
        )

    def start_write(self):
        """Trigger at least one call to handle_write() if can_write is True.

        Used to start writing to a client not triggered by a client request.
        """

        assert not self._closed

        write_buffer = bytearray()

        def can_write_cb(sock, flags, *args):
            if flags & (GLib.IOCondition.HUP | GLib.IOCondition.ERR):
                self.close()
                return False

            if flags & GLib.IOCondition.OUT:
                if self.can_write():
                    write_buffer.extend(self.handle_write())
                if not write_buffer:
                    self._out_id = None
                    return False

                while True:
                    try:
                        result = sock.send(write_buffer)
                    except OSError as e:
                        if e.errno in (errno.EWOULDBLOCK, errno.EAGAIN):
                            return True
                        if e.errno == errno.EINTR:
                            continue
                        self.close()
                        return False
                    break

                del write_buffer[:result]

            return True

        if self._out_id is None:
            self._out_id = io_add_watch(
                self._sock,
                GLib.PRIORITY_DEFAULT,
                GLib.IOCondition.OUT | GLib.IOCondition.ERR | GLib.IOCondition.HUP,
                can_write_cb,
            )

    def close(self):
        """Close this connection. Can be called multiple times.

        handle_close() will be called last.
        """

        if self._closed:
            return
        self._closed = True

        if self._in_id is not None:
            GLib.source_remove(self._in_id)
            self._in_id = None
        if self._out_id is not None:
            GLib.source_remove(self._out_id)
            self._out_id = None

        self.handle_close()
        self._server._remove_connection(self)
        self._sock.close()

    def handle_init(self, server):
        """Called first, gets passed the BaseServer instance"""

        raise NotImplementedError

    def handle_read(self, data):
        """Called if new data was read"""

        raise NotImplementedError

    def handle_write(self):
        """Called if new data can be written, should return the data"""

        raise NotImplementedError

    def can_write(self):
        """Should return True if handle_write() can return data"""

        raise NotImplementedError

    def handle_close(self):
        """Called last when the connection gets closed"""

        raise NotImplementedError
