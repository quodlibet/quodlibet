# -*- coding: utf-8 -*-
# Copyright 2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from datetime import datetime
from gi.repository import Gtk
from os import path

from quodlibet import print_d
from quodlibet.qltk.getstring import GetStringDialog
from quodlibet.util import enum
from quodlibet.util.path import normalize_path

SOUNDCLOUD_NAME = "Soundcloud"
PROCESS_QL_URLS = True

DEFAULT_BITRATE = 128
EPOCH = datetime(1970, 1, 1)
SITE_URL = "http://soundcloud.com"
IMAGE_DIR = normalize_path(
    path.join(path.dirname(__file__), '../../images/branding/soundcloud'))


def _local_image(filename):
    """
    Get a local branding image from disk
    TODO: load these from the web (and cache)
    """
    return Gtk.Image.new_from_file(path.join(IMAGE_DIR, filename))

LOGO_IMAGE_BLACK = _local_image('soundcloud-logo-black-104x16.png')


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

"""Login-state-based data for configuring actions (e.g. in the button)"""
LOGIN_STATE_DATA = {
    State.LOGGED_IN: (_("Log out of %s") % SOUNDCLOUD_NAME,
                      _local_image('btn-disconnect-l.png')),
    State.LOGGING_IN: (_("Enter code…"), None),
    State.LOGGED_OUT: (_("Log in to %s") % SOUNDCLOUD_NAME,
                       _local_image('btn-connect-l.png')),
}


@enum
class FilterType(int):
    SEP, SEARCH, FAVORITES = range(3)


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
