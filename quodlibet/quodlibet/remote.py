# -*- coding: utf-8 -*-
# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

from quodlibet.util import fifo
from quodlibet import const
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
        """Send data to the existing instance if possible.

        Raises RemoteError in case the message couldn't be send.
        """

        raise NotImplemented

    @classmethod
    def send_message_reply(cls, message):
        """Send data to the existing instance if possible and returns
        a response.

        Raises RemoteError in case the message couldn't be send or
        there was no response.
        """

        raise NotImplemented

    def start(self):
        """Start the listener for other instances"""

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
    def send_message(cls, message, reply=False):
        try:
            winpipe.write_pipe(cls._NAME, message)
        except EnvironmentError as e:
            raise RemoteError(e)

    @classmethod
    def send_message_reply(cls, message):
        raise RemoteError("not implemented")

    def start(self):
        self._server.start()

    def stop(self):
        self._server.stop()

    def _callback(self, data):
        for line in data.splitlines():
            self._cmd_registry.handle_line(self._app, line)


class QuodLibetUnixRemote(RemoteBase):

    _PATH = const.CONTROL

    def __init__(self, app, cmd_registry):
        self._app = app
        self._cmd_registry = cmd_registry
        self._fifo = fifo.FIFO(self._PATH, self._callback)

    @classmethod
    def remote_exists(cls):
        return fifo.fifo_exists(cls._PATH)

    @classmethod
    def send_message(cls, message, reply=False):
        try:
            fifo.write_fifo(cls._PATH, message)
        except EnvironmentError as e:
            raise RemoteError(e)

    @classmethod
    def send_message_reply(cls, message):
        try:
            return fifo.write_fifo_reply(cls._PATH, message)
        except EnvironmentError as e:
            raise RemoteError(e)

    def start(self):
        self._fifo.open()

    def stop(self):
        self._fifo.destroy()

    def _callback(self, data):
        for line in data.splitlines():
            self._cmd_registry.handle_line(self._app, line)


if os.name == "nt":
    Remote = QuodLibetWinRemote
else:
    Remote = QuodLibetUnixRemote
