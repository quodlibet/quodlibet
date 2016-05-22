# -*- coding: utf-8 -*-
# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

from quodlibet.util import fifo, print_w
from quodlibet import get_user_dir
try:
    from quodlibet.util import winpipe
except ImportError:
    winpipe = None


class RemoteError(Exception):
    pass


class RemoteBase(object):
    """A thing for communicating with existing instances of ourself."""

    def __init__(self, app, cmd_registry):
        """Takes an Application and CommandRegistry"""

        raise NotImplemented

    @classmethod
    def remote_exists(self):
        """See if another instance exists"""

        raise NotImplemented

    @classmethod
    def send_message(cls, message):
        """Send data to the existing instance if possible and returns
        a response.

        Raises RemoteError in case the message couldn't be send or
        there was no response.
        """

        raise NotImplemented

    def start(self):
        """Start the listener for other instances.

        Might raise RemoteError in case another instance is already listening.
        """

        raise NotImplemented

    def stop(self):
        """Stop the listener for other instances"""

        raise NotImplemented


class QuodLibetWinRemote(RemoteBase):

    _NAME = "quodlibet"

    def __init__(self, app, cmd_registry):
        self._app = app
        self._cmd_registry = cmd_registry
        self._server = winpipe.NamedPipeServer(self._NAME, self._callback)

    @classmethod
    def remote_exists(cls):
        return winpipe.pipe_exists(cls._NAME)

    @classmethod
    def send_message(cls, message):
        try:
            winpipe.write_pipe(cls._NAME, message)
        except EnvironmentError as e:
            raise RemoteError(e)

    def start(self):
        try:
            self._server.start()
        except winpipe.NamedPipeServerError as e:
            raise RemoteError(e)

    def stop(self):
        self._server.stop()

    def _callback(self, data):
        self._cmd_registry.handle_line(self._app, data)


class QuodLibetUnixRemote(RemoteBase):

    _FIFO_NAME = "control"
    _PATH = os.path.join(get_user_dir(), _FIFO_NAME)

    def __init__(self, app, cmd_registry):
        self._app = app
        self._cmd_registry = cmd_registry
        self._fifo = fifo.FIFO(self._PATH, self._callback)

    @classmethod
    def remote_exists(cls):
        return fifo.fifo_exists(cls._PATH)

    @classmethod
    def send_message(cls, message):
        try:
            return fifo.write_fifo(cls._PATH, message)
        except EnvironmentError as e:
            raise RemoteError(e)

    def start(self):
        try:
            self._fifo.open()
        except fifo.FIFOError as e:
            raise RemoteError(e)

    def stop(self):
        self._fifo.destroy()

    def _callback(self, data):
        try:
            messages = list(fifo.split_message(data))
        except ValueError:
            print_w("invalid message: %r" % data)
            return
        for command, path in messages:
            response = self._cmd_registry.handle_line(self._app, command)
            if path is not None:
                with open(path, "wb") as h:
                    if response is not None:
                        h.write(response)


if os.name == "nt":
    Remote = QuodLibetWinRemote
else:
    Remote = QuodLibetUnixRemote
