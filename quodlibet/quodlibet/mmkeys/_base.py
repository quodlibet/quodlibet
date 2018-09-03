# -*- coding: utf-8 -*-
# Copyright 2014 Christoph Reiter
#           2018 Ludovic Druette
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


class MMKeysImportError(ImportError):
    pass


class MMKeysAction(object):
    PLAY = "play"
    STOP = "stop"
    PAUSE = "pause"
    PREV = "prev"
    NEXT = "next"
    PLAYPAUSE = "playpause"
    FORWARD = "forward"
    REWIND = "rewind"
    REPEAT = "repeat"
    SHUFFLE = "shuffle"


class MMKeysBackend(object):

    def __init_(self, name, callback):
        """Callback will be called in the main thread and gets
        passed an MMKeysAction. `name` should be the application name.
        """

        raise NotImplementedError

    @classmethod
    def is_active(cls):
        """Should return if the backend should be used"""
        return True

    def grab(self):
        """Should tell the backend that the application was active
        (e.g. the main window got focused)
        """
        pass

    def cancel(self):
        """After cancel returns the callback will no longer be called.
        Can be called multiple times.
        """
        raise NotImplementedError
