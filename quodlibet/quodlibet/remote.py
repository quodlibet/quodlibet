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
    def send_message(cls, message):
        try:
            winpipe.write_pipe(cls._NAME, message)
        except EnvironmentError as e:
            raise RemoteError(e)

    def start(self):
        self._server.start()

    def stop(self):
        self._server.stop()

    def _callback(self, data):
        self._cmd_registry.handle_line(self._app, data)


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
    def send_message(cls, message):
        try:
            return fifo.write_fifo(cls._PATH, message)
        except EnvironmentError as e:
            raise RemoteError(e)

    def start(self):
        self._fifo.open()

    def stop(self):
        self._fifo.destroy()

    def _callback(self, data):
        try:
            data, path = fifo.split_message(data)
        except ValueError:
            # in case someones writes to the fifo the path part is missing
            # so call the command and throw away the response
            self._cmd_registry.handle_line(self._app, data)
        else:
            with open(path, "wb") as h:
                response = self._cmd_registry.handle_line(self._app, data)
                if response is not None:
                    h.write(response)


if os.name == "nt":
    Remote = QuodLibetWinRemote
else:
    Remote = QuodLibetUnixRemote
