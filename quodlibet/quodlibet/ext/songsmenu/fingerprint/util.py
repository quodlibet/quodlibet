# Copyright 2011,2013,2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import time
import threading

from quodlibet import config


def get_api_key():
    """The user API key for submissions"""

    return config.get("plugins", "fingerprint_acoustid_api_key", "")


def get_write_mb_tags():
    return config.getboolean("plugins", "fingerprint_write_mb_tags", False)


def get_group_by_dir():
    return config.getboolean("plugins", "fingerprint_group_by_dir", True)


class GateKeeper(object):

    def __init__(self, requests_per_sec):
        self._period = 1 / float(requests_per_sec)
        self._last = 0
        self._lock = threading.Lock()

    def wait(self):
        """Block until a new request can be made."""

        while 1:
            with self._lock:
                current = time.time()
                if abs(current - self._last) >= self._period:
                    self._last = current
                    break
                time.sleep(self._period / 10)
