# Copyright 2014 Christoph Reiter <reiter.christoph@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

"""A reactive tcp server"""

import socket
import errno

from gi.repository import Gio, GLib


DEBUG = False


class ServerError(Exception):
    pass


class BaseTCPServer(object):

    def __init__(self, port, connection_class):
        """port -- IP port
        connection_class -- BaseTCPConnection subclass
        """

        self._connections = []
        self._port = port
        self._connection_class = connection_class
        self._sock_service = None

    def start(self):
        """Start accepting connections.

        May raise ServerError.
        """

        assert not self._sock_service

        service = Gio.SocketService.new()
        try:
            service.add_inet_port(self._port, None)
        except GLib.GError as e:
            raise ServerError(e)
        service.connect("incoming", self._incoming_connection_cb)
        service.start()
        self._sock_service = service

    def stop(self):
        """Stop accepting connections and close all existing connections.

        Can be called multiple times.
        """

        if not self._sock_service:
            return

        if self._sock_service.is_active():
            self._sock_service.stop()

        for conn in list(self._connections):
            conn.close()

        assert not self._connections, self._connections

    def _remove_connection(self, conn):
        """Called by the connection class on close"""

        self._connections.remove(conn)
        del conn._gio_connection

    def _incoming_connection_cb(self, service, connection, *args):
        fd = connection.get_socket().get_fd()
        sock = socket.fromfd(fd, socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(0)

        tcp_conn = self._connection_class(self, sock)
        self._connections.append(tcp_conn)
        # XXX: set unneeded `connection` to keep the reference
        tcp_conn._gio_connection = connection
        tcp_conn.handle_init(self)


class BaseTCPConnection(object):
    """Abstract base class for TCP connections.

    Subclasses need to implement the handle_*() can_*() methods.
    """

    def __init__(self, server, sock):
        self._server = server
        self._sock = sock

        self._in_id = None
        self._out_id = None
        self._closed = False

    def log(self, msg):
        if DEBUG:
            print_d("[%d] %s" % (self._sock.fileno(), msg))

    def start_read(self):
        """Start to read and call handle_read() if data is available.

        Only call once.
        """

        assert self._in_id is None

        def can_read_cb(sock, flags, *args):
            if flags & (GLib.IOCondition.HUP | GLib.IOCondition.ERR):
                self.close()
                return False

            if flags & GLib.IOCondition.IN:
                while True:
                    try:
                        data = sock.recv(4096)
                    except (IOError, OSError) as e:
                        if e.errno in (errno.EWOULDBLOCK, errno.EAGAIN):
                            return True
                        elif e.errno == errno.EINTR:
                            continue
                        else:
                            self.close()
                            return False
                    break

                if not data:
                    self.close()
                    return False

                self.handle_read(data)
                self.start_write()

            return True

        self._in_id = GLib.io_add_watch(
            self._sock, GLib.PRIORITY_DEFAULT,
            GLib.IOCondition.IN | GLib.IOCondition.ERR | GLib.IOCondition.HUP,
            can_read_cb)

    def start_write(self):
        """Trigger at least one call to handle_write() if can_write is True.

        Used to start writing to a client not triggered by a client request.
        """

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
                    except (IOError, OSError) as e:
                        if e.errno in (errno.EWOULDBLOCK, errno.EAGAIN):
                            return True
                        elif e.errno == errno.EINTR:
                            continue
                        else:
                            self.close()
                            return False
                    break

                del write_buffer[:result]

            return True

        if self._out_id is None:
            self._out_id = GLib.io_add_watch(
                self._sock, GLib.PRIORITY_DEFAULT,
                GLib.IOCondition.OUT | GLib.IOCondition.ERR |
                GLib.IOCondition.HUP,
                can_write_cb)

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
