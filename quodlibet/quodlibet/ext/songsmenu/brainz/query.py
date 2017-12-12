# -*- coding: utf-8 -*-
# Copyright 2005-2010   Joshua Kwan <joshk@triplehelix.org>,
#                       Michael Ball <michael.ball@gmail.com>,
#                       Steven Robertson <steven@strobe.cc>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import threading
import time

from gi.repository import GLib

from quodlibet.util import print_exc


class QueryThread(object):
    """Daemon thread which does HTTP retries and avoids flooding."""

    def __init__(self):
        self.running = True
        self.queue = []
        thread = threading.Thread(target=self.__run)
        thread.daemon = True
        thread.start()

    def add(self, callback, func, *args, **kwargs):
        """Add a func to be evaluated in a background thread.
        Callback will be called with the result from the main thread.
        """

        self.queue.append((callback, func, args, kwargs))

    def stop(self):
        """Stop the background thread."""

        self.running = False

    def __run(self):
        while self.running:
            if self.queue:
                callback, func, args, kwargs = self.queue.pop(0)
                try:
                    res = func(*args, **kwargs)
                except:
                    time.sleep(2)
                    try:
                        res = func(*args, **kwargs)
                    except:
                        print_exc()
                        res = None

                def idle_check(cb, res):
                    if self.running:
                        cb(res)
                GLib.idle_add(idle_check, callback, res)
            time.sleep(1)
