# Copyright 2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from datetime import datetime

from quodlibet import print_d, _
from quodlibet.qltk import WebImage
from quodlibet.qltk.getstring import GetStringDialog
from quodlibet.util import enum

SOUNDCLOUD_NAME = "Soundcloud"
PROCESS_QL_URLS = True

DEFAULT_BITRATE = 128
EPOCH = datetime(1970, 1, 1)
SITE_URL = "https://soundcloud.com"


class Wrapper(object):
    """Object-like wrapper for read-only dictionaries"""

    def __init__(self, data):
        self.data = data

    def __getattr__(self, name):
        if name in self.data:
            return self.data.get(name)
        raise AttributeError("'%s' not found" % (name,))

    def __getitem__(self, item):
        return self.data[item]

    def __setitem__(self, key, value):
        raise NotImplementedError

    def get(self, name, default=None):
        return self.data.get(name, default)

    def __str__(self):
        return "<Wrapped: %s>" % self.data


def json_callback(wrapped):
    """Decorator for `download_json` callbacks, handling common errors"""

    def _callback(self, message, json, data):
        if json is None:
            print_d('Invalid JSON ({message.status_code}): '
                    '{message.response_body.data} (request: {data})'
                    .format(**locals()))
            return
        if 'errors' in json:
            raise ValueError("Got HTTP %d (%s)" % (message.status_code,
                                                   json['errors']))
        if 'error' in json:
            raise ValueError("Got HTTP %d (%s)" % (message.status_code,
                                                   json['error']))
        return wrapped(self, json)

    return _callback


def clamp(val, low, high):
    intval = int(val or 0)
    return max(low, min(high, intval))


@enum
class State(int):
    LOGGED_OUT, LOGGING_IN, LOGGED_IN = range(3)


@enum
class FilterType(int):
    SEARCH, FAVORITES, MINE = range(3)


class EnterAuthCodeDialog(GetStringDialog):
    def __init__(self, parent):
        super(EnterAuthCodeDialog, self).__init__(
            parent,
            _("Soundcloud authorisation"),
            _("Enter Soundcloud auth code:"),
            button_icon=None)

    def _verify_clipboard(self, text):
        if len(text) > 10:
            return text


def sanitise_tag(value):
    """QL doesn't want newlines in tags, but they Soundcloud ones
     are not always best represented as multi-value tags (comments, etc)
    """
    return (value or '').replace('\n', '\t').replace('\r', '')


def sc_btn_image(path, w, h):
    return WebImage('https://connect.soundcloud.com/2/btn-%s.png' % path, w, h)
