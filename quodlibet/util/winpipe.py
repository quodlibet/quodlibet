# Copyright 2014,2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import threading
import ctypes

from quodlibet.util.dprint import print_w

if os.name == "nt":
    from . import winapi

from gi.repository import GLib


def write_pipe(pipe_name, data):
    """Writes the data to the pipe or raises EnvironmentError"""

    assert isinstance(data, bytes)

    # XXX: otherwise many consecutive open fail, no idea..
    pipe_exists(pipe_name)

    filename = NamedPipeServer._get_filename(pipe_name)
    with open(filename, "wb") as h:
        h.write(data)


def pipe_exists(pipe_name):
    """Returns True if the named pipe named 'pipe_name' currently exists"""

    timeout_ms = 1
    filename = NamedPipeServer._get_filename(pipe_name)

    try:
        if winapi.WaitNamedPipeW(filename, timeout_ms) == 0:
            raise ctypes.WinError()
    except OSError:
        return False
    return True


class NamedPipeServerError(Exception):
    pass


class NamedPipeServer(threading.Thread):
    """A named pipe for Windows.

    * server:
        server = NamedPipeServer("foo", lambda data: ...)
        server.start()
        glib_loop()
        server.stop()

    * client:
        with open(NamedPipeServer.get_filename("foo"), "wb") as h:
            h.write("Hello World")

    """

    def __init__(self, name, callback):
        """name is the name of the pipe file (should be unique I guess)
        callback will be called with new data until close() is called.
        """

        super().__init__()
        self._event = threading.Event()
        self._filename = self._get_filename(name)
        self._callback = callback
        self._stopped = False

    @classmethod
    def _get_filename(cls, name):
        return f"\\\\.\\pipe\\{name}"

    def _process(self, data):
        def idle_process(data):
            if not self._stopped:
                self._callback(data)
            return False

        GLib.idle_add(idle_process, data)

    def start(self):
        super().start()
        # make sure we can use write_pipe() immediately after this returns
        self._event.wait()
        if self._stopped:
            # something went wrong (maybe another instance is running)
            raise NamedPipeServerError("Setting up named pipe failed")

    def run(self):
        buffer_size = 4096

        try:
            handle = winapi.CreateNamedPipeW(
                self._filename,
                (winapi.PIPE_ACCESS_INBOUND | winapi.FILE_FLAG_FIRST_PIPE_INSTANCE),
                (
                    winapi.PIPE_TYPE_BYTE
                    | winapi.PIPE_READMODE_BYTE
                    | winapi.PIPE_WAIT
                    | winapi.PIPE_REJECT_REMOTE_CLIENTS
                ),
                winapi.PIPE_UNLIMITED_INSTANCES,
                buffer_size,
                buffer_size,
                winapi.NMPWAIT_USE_DEFAULT_WAIT,
                None,
            )

            if handle == winapi.INVALID_HANDLE_VALUE:
                raise ctypes.WinError()

        except OSError:
            # due to FILE_FLAG_FIRST_PIPE_INSTANCE and not the first instance
            self._stopped = True
            self._event.set()
            return

        self._event.set()

        while 1:
            data = bytearray()
            try:
                if winapi.ConnectNamedPipe(handle, None) == 0:
                    raise ctypes.WinError()

                while 1:
                    readbuf = ctypes.create_string_buffer(buffer_size)
                    bytesread = winapi.DWORD()
                    try:
                        if (
                            winapi.ReadFile(
                                handle,
                                readbuf,
                                buffer_size,
                                ctypes.byref(bytesread),
                                None,
                            )
                            == 0
                        ):
                            raise ctypes.WinError()
                    except OSError:
                        break
                    else:
                        message = readbuf[: bytesread.value]

                    data += message

                if winapi.DisconnectNamedPipe(handle) == 0:
                    raise ctypes.WinError()
            except OSError as e:
                # better not loop forever...
                print_w(f"Error during pipe communication: {e}")
                break
            finally:
                if self._stopped:
                    break  # noqa
                if data:
                    self._process(bytes(data))

        # ignore errors here..
        winapi.CloseHandle(handle)

    def stop(self):
        """After this returns the callback will no longer be called.
        Can be called multiple times.
        """

        self._event.wait()
        if self._stopped:
            return

        self._stopped = True
        try:
            with open(self._filename, "wb") as h:
                h.write(b"stop!")
        except OSError:
            pass

        self._callback = None

        self.join()
