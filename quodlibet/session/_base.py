# Copyright 2018 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


class SessionError(Exception):
    pass


class SessionClient:
    def open(self, app):
        """Raises SessionError"""

    def close(self):
        """Doesn't raise, can be called multiple times"""
