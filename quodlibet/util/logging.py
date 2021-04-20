# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from __future__ import absolute_import

import collections
import threading


class Logs:
    """Thread safe log store"""

    MAX_LOG_SIZE_DEFAULT = 500

    def __init__(self, max_log_size=MAX_LOG_SIZE_DEFAULT):
        self._iter_lock = threading.Lock()
        self._log = collections.deque(maxlen=max_log_size)

    def _save_iter(self):
        # only pop/append/len are threadsafe, implement iter with them
        with self._iter_lock:
            temp = collections.deque()
            for i in range(len(self._log)):
                item = self._log.popleft()
                yield item
                temp.append(item)

            while temp:
                self._log.appendleft(temp.pop())

    def log(self, string, category=None):
        """Log str/unicode.

        Thread safe.
        """

        self._log.append((category, string))

    def clear(self):
        """Remove all entries.

        Thread safe.
        """

        with self._iter_lock:
            for i in range(len(self._log)):
                self._log.popleft()

    def get_content(self, category=None, limit=None):
        """Get a list of unicode strings for the specified category.
        Oldest entry first. Passing no category will return all content.
        If `limit` is specified, the last `limit` items will be returned.

        Thread safe.
        """

        content = []
        for cat, string in self._save_iter():
            if category is None or category == cat:
                if isinstance(string, bytes):
                    string = string.decode("utf-8", "replace")
                content.append(string)

        if limit is not None:
            assert limit > 0
            return content[-limit:]
        return content


_logs = Logs()
log = _logs.log
get_content = _logs.get_content
