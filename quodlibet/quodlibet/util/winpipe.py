# -*- coding: utf-8 -*-
# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import threading

import win32pipe
import win32file
import pywintypes

from gi.repository import GLib


def write_pipe(pipe_name, data):
    """Writes the data to the pipe or raises EnvironmentError"""

    # XXX: otherwise many consecutive open fail, no idea..
    pipe_exists(pipe_name)

    with open(NamedPipeServer._get_filename(pipe_name), "wb") as h:
        h.write(data)


def pipe_exists(pipe_name):
    """Returns True if the named pipe named 'pipe_name' currently exists"""

    try:
        win32pipe.WaitNamedPipe(NamedPipeServer._get_filename(pipe_name), 1)
    except pywintypes.error:
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

        super(NamedPipeServer, self).__init__()
        self._event = threading.Event()
        self._filename = self._get_filename(name)
        self._callback = callback
        self._stopped = False

    @classmethod
    def _get_filename(cls, name):
        return ur'\\.\pipe\%s' % name

    def _process(self, data):
        def idle_process(data):
            if not self._stopped:
                self._callback(data)
            return False

        GLib.idle_add(idle_process, data)

    def start(self):
        super(NamedPipeServer, self).start()
        # make sure we can use write_pipe() immediately after this returns
        self._event.wait()
        if self._stopped:
            # something went wrong (maybe another instance is running)
            raise NamedPipeServerError("Setting up named pipe failed")

    def run(self):
        # REJECT doesn't do anything under XP, but XP is gone anyway
        PIPE_REJECT_REMOTE_CLIENTS = 0x00000008
        FILE_FLAG_FIRST_PIPE_INSTANCE = 0x00080000
        buffer_ = 4096
        timeout_ms = 50

        try:
            handle = win32pipe.CreateNamedPipe(
                self._filename,
                win32pipe.PIPE_ACCESS_INBOUND | FILE_FLAG_FIRST_PIPE_INSTANCE,
                (win32pipe.PIPE_TYPE_BYTE | win32pipe.PIPE_READMODE_BYTE |
                 win32pipe.PIPE_WAIT | PIPE_REJECT_REMOTE_CLIENTS),
                win32pipe.PIPE_UNLIMITED_INSTANCES,
                buffer_,
                buffer_,
                timeout_ms,
                None)
        except pywintypes.error:
            # due to FILE_FLAG_FIRST_PIPE_INSTANCE and not the first instance
            self._stopped = True
            self._event.set()
            return

        if handle == win32file.INVALID_HANDLE_VALUE:
            self._stopped = True
            self._event.set()
            return

        self._event.set()

        while 1:
            data = bytearray()
            try:
                win32pipe.ConnectNamedPipe(handle)

                while 1:
                    try:
                        code, message = win32file.ReadFile(
                            handle, buffer_, None)
                    except pywintypes.error:
                        break
                    data += message

                win32pipe.DisconnectNamedPipe(handle)
            except pywintypes.error:
                # better not loop forever..
                break
            finally:
                if self._stopped:
                    break
                if data:
                    self._process(bytes(data))

        try:
            win32file.CloseHandle(handle)
        except pywintypes.error:
            pass

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
                h.write("stop!")
        except EnvironmentError:
            pass

        self._callback = None

        self.join()
